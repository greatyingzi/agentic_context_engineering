#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, Optional

from common import (
    format_playbook,
    generate_task_guidance,
    get_anthropic_client,
    get_exception_handler,
    infer_tags_from_text,
    is_diagnostic_mode,
    load_playbook,
    load_template,
    load_transcript,
    normalize_tags,
    save_diagnostic,
    select_relevant_keypoints,
)

# Configuration constants for better maintainability
MAX_CONVERSATION_MESSAGES = 12  # Number of recent messages to include in context
MAX_SEED_TAGS = 4  # Maximum tags to infer from prompt
MAX_CONTEXT_KEYPOINTS = 5  # Maximum key points to include in guidance context (legacy, not used with precision injection)
MAX_TAGS_FINAL = 6  # Maximum final tags after normalization
TAGS_GENERATION_MAX_TOKENS = 1024  # Max tokens for tag generation
GUIDANCE_GENERATION_MAX_TOKENS = 2048  # Max tokens for guidance generation
MAX_SELECTED_KEYPOINTS = 25  # Maximum key points to select for context


def extract_json_from_response(response_text: str) -> Optional[Dict[Any, Any]]:
    """Extract JSON from LLM response with robust fallback handling.

    Handles responses wrapped in ```json...``` or ```...``` blocks,
    or plain JSON strings. Returns None if JSON cannot be parsed.
    """
    if not response_text.strip():
        return None

    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip() if end > start else ""
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip() if end > start else ""
    else:
        json_text = response_text.strip()

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None


def generate_tags_only(
    messages: list,
    prompt_text: str = "",
    playbook: Optional[dict] = None,
    diagnostic_name: str = "tags_only",
) -> dict:
    """Generate tags only (no guidance).

    This is Phase 1 of the two-phase workflow - just generate and return tags.
    """
    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for tag generation", diagnostic_name)
        return {
            "tags": {
                "final_tags": [],
                "seed_tags": [],
                "reasoning": "No client available",
            }
        }

    # Get existing tags from playbook key_points
    existing_tags = []
    if playbook and "key_points" in playbook:
        tags_set = set()
        for kp in playbook["key_points"]:
            kp_tags = kp.get("tags", [])
            if isinstance(kp_tags, list):
                tags_set.update(kp_tags)
        existing_tags = list(tags_set)

    # Infer seed tags from prompt
    prompt_seed_tags = normalize_tags(
        infer_tags_from_text(prompt_text, max_tags=MAX_SEED_TAGS)
    )

    # Build format params for tag-only prompt
    format_params = {
        "conversation": json.dumps(
            messages[-MAX_CONVERSATION_MESSAGES:] if messages else [],
            indent=2,
            ensure_ascii=False,
        ),
        "prompt": prompt_text,
    }

    if existing_tags:
        existing_tags_context = f"Available tags: {json.dumps(sorted(existing_tags))}"
        format_params["existing_tags_context"] = existing_tags_context
    else:
        format_params["existing_tags_context"] = "No existing tags available."

    # Load tag-only template (reuse task_guidance template but ignore guidance part)
    template = load_template("task_guidance.txt")
    prompt = template.format(**format_params)

    response = client.messages.create(
        model=model,
        max_tokens=TAGS_GENERATION_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# TAGS-ONLY PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        # Fallback to seed tags
        final_tags = prompt_seed_tags
        if is_diagnostic_mode():
            save_diagnostic(
                f"EMPTY RESPONSE - LLM returned empty response\n\n"
                f"Fall back to {len(prompt_seed_tags)} seed tags: {prompt_seed_tags}\n"
                f"Prompt text preview: {prompt_text[:200]}...",
                f"{diagnostic_name}_empty_response"
            )
    else:
        # Parse JSON response using common function
        parsed = extract_json_from_response(response_text)

        if parsed:
            tags_data = parsed.get("tags", {})
            if isinstance(tags_data, dict) and "final_tags" in tags_data:
                llm_tags = [
                    t for t in tags_data.get("final_tags", []) if isinstance(t, str)
                ]
            else:
                llm_tags = [t for t in tags_data if isinstance(t, str)]
        else:
            # Fallback to seed tags
            llm_tags = prompt_seed_tags
            if is_diagnostic_mode():
                save_diagnostic(
                    f"JSON PARSE FAILED - Could not parse LLM response\n\n"
                    f"Response preview: {response_text[:500]}...\n\n"
                    f"Fall back to {len(prompt_seed_tags)} seed tags: {prompt_seed_tags}",
                    f"{diagnostic_name}_json_parse_failed"
                )

        # Combine and normalize tags
        final_tags = normalize_tags(
            prompt_seed_tags + llm_tags, max_tags=MAX_TAGS_FINAL
        )
        final_tags = final_tags or prompt_seed_tags

        # Final check: if still no tags, add diagnostic
        if not final_tags and is_diagnostic_mode():
            save_diagnostic(
                f"NO TAGS GENERATED - All fallback strategies failed\n\n"
                f"Seed tags: {prompt_seed_tags}\n"
                f"LLM tags: {llm_tags}\n"
                f"Combined (pre-normalization): {prompt_seed_tags + llm_tags}\n"
                f"Final (post-normalization): {final_tags}",
                f"{diagnostic_name}_no_final_tags"
            )

    return {
        "tags": {
            "final_tags": final_tags,
            "seed_tags": prompt_seed_tags,
            "reasoning": "Tags generated in Phase 1",
        },
        "injection_settings": {
            "temperature": parsed.get("injection_settings", {}).get("temperature", 0.5)
            if parsed
            else 0.5,
            "reasoning": parsed.get("injection_settings", {}).get(
                "reasoning", "Default temperature"
            )
            if parsed
            else "Default temperature",
        },
    }


def generate_context_aware_guidance(
    messages: list,
    prompt_text: str,
    matched_keypoints: list[dict],
    tags: list[str],
    playbook: dict,
    diagnostic_name: str = "context_aware_guidance",
) -> dict:
    """Generate guidance that's aware of matched key points.

    This is Phase 2 of the two-phase workflow - generate guidance with context of matched kpts.
    """
    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic(
                "no client available for guidance generation", diagnostic_name
            )
        return {
            "complexity": "moderate",
            "brief_guidance": "Cannot assess without client",
        }

    # Prepare context from matched key points with IDs
    kpts_context = ""
    if matched_keypoints:
        # Use more kpts for context during guidance generation (not limiting to MAX_CONTEXT_KEYPOINTS)
        # This ensures the LLM has enough context to make informed recommendations
        kpts_context = "\n".join(
            [
                f"- {kp.get('name', 'unknown')}: {kp.get('text', '')}"
                for kp in matched_keypoints[
                    :MAX_SELECTED_KEYPOINTS
                ]  # Use the larger limit for guidance generation
            ]
        )

    # Build context-aware guidance prompt
    format_params = {
        "conversation": json.dumps(
            messages[-MAX_CONVERSATION_MESSAGES:] if messages else [],
            indent=2,
            ensure_ascii=False,
        ),
        "prompt": prompt_text,
        "matched_keypoints": kpts_context,
        "tags": ", ".join(tags),
        "has_keypoints": "Yes" if kpts_context else "No",
        "existing_tags_context": f"Generated tags: {', '.join(tags)}",
    }

    template = load_template("task_guidance_with_kpts.txt")

    # Use a safer template replacement method that handles JSON braces properly
    prompt = template
    for key, value in format_params.items():
        # Use replace instead of format to avoid JSON brace conflicts
        placeholder = "{" + key + "}"
        prompt = prompt.replace(placeholder, str(value))

    response = client.messages.create(
        model=model,
        max_tokens=GUIDANCE_GENERATION_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# CONTEXT-AWARE GUIDANCE PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        if is_diagnostic_mode():
            save_diagnostic(
                f"EMPTY GUIDANCE RESPONSE - LLM returned empty response\n\n"
                f"Matched keypoints: {len(matched_keypoints)} items\n"
                f"Tags: {tags}\n"
                f"Kpts context length: {len(kpts_context)} chars",
                f"{diagnostic_name}_empty_response"
            )
        return {"complexity": "moderate", "brief_guidance": ""}
    else:
        # Parse JSON response using common function
        parsed = extract_json_from_response(response_text)

        if parsed:
            guidance_result = parsed.get("task_guidance", {})
            recommended_kpt_ids = parsed.get("recommended_kpt_ids", [])
            # Ensure required fields exist
            if "brief_guidance" not in guidance_result:
                guidance_result["brief_guidance"] = ""
            if "complexity" not in guidance_result:
                guidance_result["complexity"] = "moderate"
        else:
            if is_diagnostic_mode():
                save_diagnostic(
                    f"GUIDANCE JSON PARSE FAILED - Could not parse LLM response\n\n"
                    f"Response preview: {response_text[:500]}...\n\n"
                    f"Matched keypoints: {len(matched_keypoints)}\n"
                    f"Tags: {tags}",
                    f"{diagnostic_name}_json_parse_failed"
                )
            guidance_result = {
                "complexity": "moderate",
                "brief_guidance": "Failed to parse guidance response",
            }
            recommended_kpt_ids = []

    # Return both guidance result and recommended kpt ids
    return {
        "guidance": guidance_result,
        "recommended_kpt_ids": recommended_kpt_ids
    }


def format_context_with_separate_sections(
    selected_key_points: list[dict],
    guidance_result: dict,
    tags: list[str],
    temperature: float = 0.5,
    recommended_kpt_ids: list[str] = None,
) -> str:
    """Format final context with separate sections for key points and guidance.

    Only injects titled content when KPT matching is confirmed.
    """
    sections = []

    # Add temperature info header
    temp_info = f"🌡️ **Temperature: {temperature:.2f}** "
    if temperature <= 0.3:
        temp_info += "(Conservative: High Confidence priority)"
    elif temperature >= 0.7:
        temp_info += "(Exploratory: Recommendation priority)"
    else:
        temp_info += "(Balanced: Mixed selection)"

    # Check if we have any matched KPTs
    key_points_to_show = []
    if recommended_kpt_ids is not None:
        # Create a set for faster lookup
        recommended_ids_set = set(recommended_kpt_ids)
        key_points_to_show = [
            kp for kp in selected_key_points
            if kp.get('name', '') in recommended_ids_set
        ]
    else:
        # Fallback to all selected points if no recommendations
        key_points_to_show = selected_key_points

    # CRITICAL: Only inject content when KPT matching is confirmed
    if not key_points_to_show:
        # No KPT matches found - return only temperature info or empty string
        # Based on user requirement: "当没有匹配到kpts时，标题也不需要注入"
        return temp_info if temp_info.strip() else ""

    # We have KPT matches - proceed with full content injection
    sections.append(temp_info)

    # Section 1: Matched Key Points (only recommended ones)
    kpts_section = "### 📚 Matched Key Points\n\n"
    for kp in key_points_to_show:
        score = kp.get("score", 0)
        layer = kp.get("_layer", "UNKNOWN")
        total_match = kp.get("_total_match", 0)

        # Layer-based styling
        if layer == "HIGH_CONFIDENCE":
            layer_emoji = "🔷"  # Blue diamond for high confidence
            layer_label = "HC"
        elif layer == "RECOMMENDATION":
            layer_emoji = "🟢"  # Green circle for recommendation
            layer_label = "RC"
        else:
            layer_emoji = "⚪"  # White circle for unknown
            layer_label = "??"

        # Format with layer, ID and score information for consistency
        kpt_id = kp.get('name', '')
        kpt_text = kp.get('text', '')
        if kpt_id:
            # Include ID for consistency with what LLM sees during guidance generation
            kpts_section += f"{layer_emoji} **[{layer_label}] {kpt_id}: {kpt_text}** (match: {total_match:.2f})\n"
        else:
            # Fallback for safety
            kpts_section += f"{layer_emoji} **[{layer_label}] {kpt_text}** (match: {total_match:.2f})\n"
    sections.append(kpts_section)

    # Section 2: Task Guidance
    # Handle both old format (direct guidance) and new format (with 'guidance' key)
    if isinstance(guidance_result, dict):
        if 'guidance' in guidance_result:
            # New format with nested 'guidance'
            guidance_data = guidance_result.get('guidance', {})
        else:
            # Old format where guidance_result is the guidance data itself
            guidance_data = guidance_result
    else:
        guidance_data = {}

    brief_guidance = guidance_data.get("brief_guidance", "")
    reasoning = guidance_data.get("reasoning", "")
    trajectory_insights = guidance_data.get("trajectory_insights", {})
    proactive_alert = guidance_data.get("proactive_alert", {})

    # Debug output
    if is_diagnostic_mode():
        print(f"🐛 DEBUG: brief_guidance = '{brief_guidance}'")
        print(f"🐛 DEBUG: guidance_data keys = {list(guidance_data.keys())}")

    # Always add trajectory insights if available (even without guidance)
    if trajectory_insights:
        trajectory_section = "### 📊 Task Trajectory Insights\n\n"

        current_phase = trajectory_insights.get("current_phase", "unknown")
        complexity_trend = trajectory_insights.get("complexity_trend", "stable")
        intent_consistency = trajectory_insights.get("intent_consistency", 0.0)
        detected_patterns = trajectory_insights.get("detected_patterns", [])

        trajectory_section += f"**Current Phase**: {current_phase}\n"
        trajectory_section += f"**Complexity Trend**: {complexity_trend}\n"
        trajectory_section += f"**Intent Consistency**: {intent_consistency:.2f}\n"

        if detected_patterns:
            patterns_str = ", ".join(detected_patterns)
            trajectory_section += f"**Detected Patterns**: {patterns_str}\n"

        sections.append(trajectory_section)

    # Always add proactive alert if present (even without guidance)
    if proactive_alert and proactive_alert.get("present", False):
        alert_section = "### 🚨 Proactive Alert\n\n"
        alert_type = proactive_alert.get("type", "unknown")
        alert_message = proactive_alert.get("message", "")
        confirmation_required = proactive_alert.get("confirmation_required", False)

        alert_section += f"**Type**: {alert_type}\n"
        if alert_message:
            alert_section += f"**Message**: {alert_message}\n"
        if confirmation_required:
            alert_section += "**User Confirmation Required**: Yes\n"

        sections.append(alert_section)

    # Add guidance section if available
    if brief_guidance.strip():
        guidance_section = "### 💡 Task Guidance\n\n"
        guidance_section += brief_guidance

        # Add reasoning if available
        if reasoning.strip():
            guidance_section += f"\n\n*Reasoning: {reasoning}*"

        sections.append(guidance_section)

    return "\n\n".join(sections)


def main():
    handler = get_exception_handler()

    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "unknown")
        prompt_text = input_data.get("prompt", "")
        transcript_path = input_data.get("transcript_path")

        playbook = load_playbook()

        messages = []
        if transcript_path:
            try:
                messages = load_transcript(transcript_path)
            except Exception:
                messages = []

        # === Phase 1: Generate tags and match key points (no guidance) ===

        # Generate tags only
        tags_result = generate_tags_only(
            messages, prompt_text, playbook=playbook, diagnostic_name="tags_generation"
        )

        tags_data = tags_result.get("tags", {})
        tags = tags_data.get("final_tags", [])
        prompt_tags = tags_data.get("seed_tags", [])

        # Extract temperature from injection settings
        injection_settings = tags_result.get("injection_settings", {})
        temperature = injection_settings.get("temperature", 0.5)

        # Match key points based on tags with temperature
        selected_key_points = select_relevant_keypoints(
            playbook,
            tags,
            limit=MAX_SELECTED_KEYPOINTS,
            prompt_tags=prompt_tags,
            temperature=temperature,
        )

        # === Phase 2: Generate context-aware guidance using matched key points ===

        # Generate guidance that's aware of matched key points
        guidance_with_recommendations = generate_context_aware_guidance(
            messages, prompt_text, selected_key_points, tags, playbook
        )

        # Extract recommended kpt IDs from the response
        recommended_kpt_ids = guidance_with_recommendations.get("recommended_kpt_ids", [])
        guidance_result = guidance_with_recommendations.get("guidance", {})

        # Format context with separate sections, using only recommended kpts
        context = format_context_with_separate_sections(
            selected_key_points, guidance_with_recommendations, tags, temperature, recommended_kpt_ids
        )

        if not context.strip():
            if is_diagnostic_mode():
                save_diagnostic(
                    f"EMPTY CONTEXT - All sections empty\n\n"
                    f"Tags: {tags} (count: {len(tags)})\n"
                    f"Selected keypoints: {len(selected_key_points)} items\n"
                    f"Keypoint names: {[kp.get('name', 'NO_NAME') for kp in selected_key_points]}\n"
                    f"Recommended kpt IDs: {recommended_kpt_ids}\n"
                    f"Guidance result type: {type(guidance_with_recommendations)}\n"
                    f"Guidance brief: {guidance_result.get('brief_guidance', 'NO_BRIEF_GUIDANCE')[:200] if guidance_result else 'NO_GUIDANCE_RESULT'}\n"
                    f"Temperature: {temperature}\n"
                    f"Formatted context length: {len(context)} characters",
                    "empty_context_analysis"
                )
            print(json.dumps({}), flush=True)
            sys.exit(0)

        if is_diagnostic_mode():
            diagnostic_payload = {
                "session_id": session_id,
                "prompt": prompt_text,
                "tags": tags,
                "prompt_tags": prompt_tags,
                "selected": [kp.get("name") for kp in selected_key_points],
                "selected_count": len(selected_key_points),
                "recommended_kpt_ids": recommended_kpt_ids,
                "recommended_count": len(recommended_kpt_ids),
                "context": context,
                "task_guidance": guidance_with_recommendations,
                "workflow": {
                    "phase": "Two-phase workflow completed",
                    "phase1": "Tags generated and kpts matched",
                    "phase2": "Context-aware guidance generated with precise recommendations",
                },
            }
            save_diagnostic(
                json.dumps(diagnostic_payload, indent=2, ensure_ascii=False),
                "user_prompt_inject",
            )

        response = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }

        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(response), flush=True)

    except Exception as e:
        # Use global exception handler for consistent error logging and user feedback
        context_data = {
            "input_data": input_data
            if "input_data" in locals()
            else "Unable to capture",
            "hook_stage": "main_execution",
        }
        handler.handle_and_exit(
            e,
            "user_prompt_inject",
            context_data,
            session_id if "session_id" in locals() else None,
        )


if __name__ == "__main__":
    main()
