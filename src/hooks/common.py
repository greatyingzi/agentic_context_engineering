#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

# Import path utilities
try:
    from .utils.path_utils import get_project_dir, get_user_claude_dir, is_diagnostic_mode, save_diagnostic
    from .utils.tag_utils import normalize_tags, infer_tags_from_text
except ImportError:
    # Fallback for direct execution or testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.path_utils import get_project_dir, get_user_claude_dir, is_diagnostic_mode, save_diagnostic
    from utils.tag_utils import normalize_tags, infer_tags_from_text

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import file utilities
try:
    from .file_utils import load_transcript, load_template
except ImportError:
    # Fallback for direct execution or testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from file_utils import load_transcript, load_template

# Import playbook engine utilities
try:
    from .playbook_engine import (
        generate_keypoint_name,
        load_settings,
        validate_playbook_structure,
        load_playbook,
        save_playbook,
        format_playbook,
        update_playbook_data,
        select_relevant_keypoints
    )
except ImportError:
    # Fallback for direct execution or testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from playbook_engine import (
        generate_keypoint_name,
        load_settings,
        validate_playbook_structure,
        load_playbook,
        save_playbook,
        format_playbook,
        update_playbook_data,
        select_relevant_keypoints
    )

# Import exception handler
try:
    from .exception_handler import (
        get_exception_handler,
        hook_exception_wrapper,
        log_hook_error,
        get_log_file_path
    )
except ImportError:
    # Fallback for direct execution or testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from exception_handler import (
        get_exception_handler,
        hook_exception_wrapper,
        log_hook_error,
        get_log_file_path
    )



def is_first_message(session_id: str) -> bool:
    session_file = get_project_dir() / ".claude" / "last_session.txt"

    if session_file.exists():
        last_session_id = session_file.read_text().strip()
        return session_id != last_session_id

    return True


def mark_session(session_id: str):
    session_file = get_project_dir() / ".claude" / "last_session.txt"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)


def clear_session():
    session_file = get_project_dir() / ".claude" / "last_session.txt"
    if session_file.exists():
        session_file.unlink()


def save_session_injections(session_id: str, injected_kpt_names: list[str]):
    """Save the list of KPT names injected during this session."""
    session_injections_file = get_project_dir() / ".claude" / "session_injections.json"

    # Load existing data
    if session_injections_file.exists():
        try:
            with open(session_injections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
    else:
        data = {}

    # Update with current session injections
    data[session_id] = {
        "injected_kpts": injected_kpt_names,
        "timestamp": datetime.now().isoformat()
    }

    # Save back
    session_injections_file.parent.mkdir(parents=True, exist_ok=True)
    with open(session_injections_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_session_injections(session_id: str) -> list[str]:
    """Load the list of KPT names injected during the specified session.

    If exact session match not found, returns injections from most recent session.
    This ensures compatibility even when session IDs change between hook invocations.
    """
    session_injections_file = get_project_dir() / ".claude" / "session_injections.json"

    if not session_injections_file.exists():
        return []

    try:
        with open(session_injections_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Try exact match first
            if session_id in data:
                return data[session_id].get("injected_kpts", [])

            # Fallback: return injections from most recent session
            if data:
                most_recent_session = max(data.items(), key=lambda x: x[1].get("timestamp", ""))
                return most_recent_session[1].get("injected_kpts", [])

            return []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def clear_session_injections(session_id: str):
    """Clear injection records for a specific session after processing."""
    session_injections_file = get_project_dir() / ".claude" / "session_injections.json"

    if not session_injections_file.exists():
        return

    try:
        with open(session_injections_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Remove the session entry
        if session_id in data:
            del data[session_id]

        # Save back if there are still sessions
        if data:
            with open(session_injections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            # Remove file if no sessions left
            session_injections_file.unlink()

    except (json.JSONDecodeError, FileNotFoundError):
        pass




def calculate_lexical_similarity(text1: str, text2: str) -> float:
    """Calculate lexical similarity using Jaccard similarity with substring matching."""
    # Handle empty strings
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0

    # Convert to lowercase
    text1_lower = text1.lower()
    text2_lower = text2.lower()

    # Check exact match
    if text1_lower == text2_lower:
        return 1.0

    # Check substring relationship (api vs apis should have high similarity)
    substring_bonus = 0.0
    if text1_lower in text2_lower or text2_lower in text1_lower:
        substring_bonus = 0.7

    # Token-based similarity
    tokens1 = set(re.findall(r'[\w_-]+', text1_lower))
    tokens2 = set(re.findall(r'[\w_-]+', text2_lower))

    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return substring_bonus

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    jaccard_similarity = len(intersection) / len(union) if union else 0.0

    # Combine Jaccard similarity with substring bonus
    final_similarity = max(jaccard_similarity, substring_bonus)

    return final_similarity


def find_similar_tags(target_tag: str, existing_tags: List[str], threshold: float = 0.8) -> List[Tuple[str, float]]:
    """Find tags that are lexically similar to the target tag.
    Returns list of (tag, similarity_score) tuples above threshold."""
    similar_tags = []

    for tag in existing_tags:
        if tag.lower() == target_tag.lower():
            # Exact match gets highest score
            similar_tags.append((tag, 1.0))
            continue

        # Calculate lexical similarity
        similarity = calculate_lexical_similarity(target_tag, tag)
        if similarity >= threshold:
            similar_tags.append((tag, similarity))

    # Sort by similarity score (descending)
    similar_tags.sort(key=lambda x: x[1], reverse=True)
    return similar_tags


MAX_KEYPOINTS = 250  # hard cap to keep playbook manageable


def get_anthropic_client() -> Tuple[Optional["anthropic.Anthropic"], Optional[str]]:
    """Return (client, model). If diagnostics are on, log why a client is missing."""
    if not ANTHROPIC_AVAILABLE:
        if is_diagnostic_mode():
            save_diagnostic("anthropic not installed", "client_missing")
        return None, None

    model = (
        os.getenv("AGENTIC_CONTEXT_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or "claude-sonnet-4-5-20250929"
    )
    if not model:
        if is_diagnostic_mode():
            save_diagnostic("model not configured", "client_missing")
        return None, None

    api_key = (
        os.getenv("AGENTIC_CONTEXT_API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        if is_diagnostic_mode():
            save_diagnostic("api key not configured", "client_missing")
        return None, None

    base_url = os.getenv("AGENTIC_CONTEXT_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")

    client = (
        anthropic.Anthropic(api_key=api_key, base_url=base_url)
        if base_url
        else anthropic.Anthropic(api_key=api_key)
    )
    return client, model


def generate_tags_from_messages(
    messages: list[dict],
    prompt_text: str = "",
    playbook: Optional[dict] = None,
    diagnostic_name: str = "tagger"
) -> tuple[list[str], list[str]]:
    """Generate request tags from recent conversation history and pending prompt.

    Args:
        messages: Recent conversation history
        prompt_text: The current prompt text
        playbook: Optional playbook containing existing tags for recommendations
        diagnostic_name: Name for diagnostic logging

    Returns:
        Tuple of (final_tags, seed_tags)
    """
    prompt_seed_tags = normalize_tags(infer_tags_from_text(prompt_text, max_tags=4))

    # Get existing tags from playbook key_points
    existing_tags = []
    if playbook and "key_points" in playbook:
        # Collect all unique tags from key_points
        tags_set = set()
        for kp in playbook["key_points"]:
            kp_tags = kp.get("tags", [])
            if isinstance(kp_tags, list):
                tags_set.update(kp_tags)
        existing_tags = list(tags_set)

    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for tagger", diagnostic_name)
        return prompt_seed_tags, prompt_seed_tags

    recent_messages = messages[-12:] if messages else []
    template = load_template("tagger.txt")

    prompt = template.format(
        conversation=json.dumps(recent_messages, indent=2, ensure_ascii=False),
        prompt=prompt_text,
        existing_tags_context="",  # Empty placeholder since we removed it from template
    )

    # Add existing tags context if we have any
    if existing_tags:
        # Provide simple tag list to help LLM understand the tag space
        existing_tags_context = f"\n\nExisting tags in playbook: {json.dumps(sorted(existing_tags))}"
        prompt += existing_tags_context

    response = client.messages.create(
        model=model, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        return prompt_seed_tags, prompt_seed_tags

    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip()
    else:
        json_text = response_text.strip()

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return prompt_seed_tags, prompt_seed_tags

    llm_tags: list[str] = []
    if isinstance(parsed, list):
        llm_tags = [t for t in parsed if isinstance(t, str)]
    elif isinstance(parsed, dict) and "tags" in parsed:
        llm_tags = [t for t in parsed.get("tags", []) if isinstance(t, str)]

    # 合并LLM生成的标签和种子标签，去重
    combined_tags = list(set(llm_tags + prompt_seed_tags))
    return combined_tags, prompt_seed_tags


def generate_task_guidance(
    messages: list[dict],
    prompt_text: str = "",
    playbook: Optional[dict] = None,
    diagnostic_name: str = "task_guidance"
) -> dict:
    """Generate tags and task-specific guidance in a single LLM call.

    Args:
        messages: Recent conversation history
        prompt_text: The current prompt text
        playbook: Optional playbook containing existing tags for recommendations
        diagnostic_name: Name for diagnostic logging

    Returns:
        Dict containing both tag analysis and task-specific guidance
    """
    prompt_seed_tags = normalize_tags(infer_tags_from_text(prompt_text, max_tags=4))

    # Get existing tags from playbook key_points
    existing_tags = []
    if playbook and "key_points" in playbook:
        # Collect all unique tags from key_points
        tags_set = set()
        for kp in playbook["key_points"]:
            kp_tags = kp.get("tags", [])
            if isinstance(kp_tags, list):
                tags_set.update(kp_tags)
        existing_tags = list(tags_set)

    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for task guidance", diagnostic_name)
        return {
            "tags": {
                "final_tags": prompt_seed_tags,
                "reasoning": "Using seed tags due to no client"
            },
            "task_guidance": {
                "complexity": "moderate",
                "show_guidance": False,
                "brief_guidance": "Cannot assess without client"
            }
        }

    # Add existing tags context if we have any
    recent_messages = messages[-12:] if messages else []
    format_params = {
        "conversation": json.dumps(recent_messages, indent=2, ensure_ascii=False),
        "prompt": prompt_text,
    }

    if existing_tags:
        # Provide simple tag list to help LLM understand tag space
        existing_tags_context = f"Available tags: {json.dumps(sorted(existing_tags))}"
        format_params["existing_tags_context"] = existing_tags_context
    else:
        # No existing tags available
        format_params["existing_tags_context"] = "No existing tags available."

    template = load_template("task_guidance.txt")
    prompt = template.format(**format_params)

    response = client.messages.create(
        model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}]
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        # Fallback to seed tags
        llm_tags = prompt_seed_tags
        guidance_result = {
            "complexity": "moderate",
            "brief_guidance": ""
        }
    else:
        # Parse JSON response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            json_text = response_text.strip()

        try:
            parsed = json.loads(json_text)

            # Extract tags
            tags_data = parsed.get("tags", {})
            if isinstance(tags_data, dict) and "final_tags" in tags_data:
                llm_tags = [t for t in tags_data.get("final_tags", []) if isinstance(t, str)]
            else:
                llm_tags = [t for t in tags_data if isinstance(t, str)]

            # Extract guidance
            guidance_result = parsed.get("task_guidance", {})

            # Handle both old and new formats
            # If old format detected, convert to new minimal format
            if "needs_clarification" in guidance_result or "clarification_questions" in guidance_result:
                # Old format detected - convert to new format
                complexity = guidance_result.get("complexity", "moderate")
                needs_clarification = guidance_result.get("needs_clarification", False)
                assessment = guidance_result.get("assessment", "")

                # Generate brief guidance from old format
                brief_guidance = ""

                if needs_clarification and "clarification_questions" in guidance_result:
                    questions = guidance_result.get("clarification_questions", [])
                    if questions:
                        brief_guidance = f"Clarify the following: {questions[0] if len(questions) > 0 else 'What are the specific requirements?'}"
                elif "suggested_approach" in guidance_result:
                    brief_guidance = guidance_result.get("suggested_approach", "")[:100] + "." if len(guidance_result.get("suggested_approach", "")) > 0 else ""

                # Create new format
                new_guidance_result = {
                    "complexity": complexity,
                    "brief_guidance": brief_guidance
                }
                guidance_result = new_guidance_result
            else:
                # New format detected - ensure required fields exist
                if "brief_guidance" not in guidance_result:
                    guidance_result["brief_guidance"] = ""

        except json.JSONDecodeError:
            # Fallback to seed tags
            llm_tags = prompt_seed_tags
            guidance_result = {
                "complexity": "moderate",
                "show_guidance": False,
                "brief_guidance": ""
            }

    # Combine and normalize tags
    combined = normalize_tags(prompt_seed_tags + llm_tags, max_tags=6)
    combined = combined or prompt_seed_tags

    return {
        "tags": {
            "final_tags": combined,
            "seed_tags": prompt_seed_tags,
            "reasoning": tags_data.get("reasoning") if 'tags_data' in locals() else "Generated"
        },
        "task_guidance": guidance_result
    }


def generate_tags_and_workflow(
    messages: list[dict],
    prompt_text: str = "",
    playbook: Optional[dict] = None,
    diagnostic_name: str = "tagger_with_workflow"
) -> dict:
    """Generate tags and workflow evaluation in a single LLM call.

    Args:
        messages: Recent conversation history
        prompt_text: The current prompt text
        playbook: Optional playbook containing existing tags for recommendations
        diagnostic_name: Name for diagnostic logging

    Returns:
        Dict containing both tag analysis and workflow evaluation results
    """
    prompt_seed_tags = normalize_tags(infer_tags_from_text(prompt_text, max_tags=4))

    # Get existing tags from playbook key_points
    existing_tags = []
    if playbook and "key_points" in playbook:
        # Collect all unique tags from key_points
        tags_set = set()
        for kp in playbook["key_points"]:
            kp_tags = kp.get("tags", [])
            if isinstance(kp_tags, list):
                tags_set.update(kp_tags)
        existing_tags = list(tags_set)

    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for tagger with workflow", diagnostic_name)
        return {
            "tags": {
                "final_tags": prompt_seed_tags,
                "reasoning": "Using seed tags due to no client"
            },
            "workflow": {
                "complexity": "moderate",
                "confidence": 0.5,
                "reasoning": "Cannot assess complexity without client",
                "needs_clarification": False,
                "needs_deep_analysis": False,
                "suggested_action": "proceed",
                "clarification_questions": [],
                "analysis_depth": 1
            }
        }

    recent_messages = messages[-12:] if messages else []
    template = load_template("tagger_with_workflow.txt")

    prompt = template.format(
        conversation=json.dumps(recent_messages, indent=2, ensure_ascii=False),
        prompt=prompt_text,
    )

    # Add existing tags context if we have any
    if existing_tags:
        # Provide simple tag list to help LLM understand tag space
        existing_tags_context = f"\n\nExisting tags in playbook: {json.dumps(sorted(existing_tags))}"
        prompt += existing_tags_context

    response = client.messages.create(
        model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}]
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        # Fallback to seed tags
        llm_tags = prompt_seed_tags
        workflow_result = {
            "complexity": "moderate",
            "confidence": 0.5,
            "reasoning": "Failed to parse response",
            "needs_clarification": False,
            "needs_deep_analysis": False,
            "suggested_action": "proceed",
            "clarification_questions": [],
            "analysis_depth": 1
        }
    else:
        # Parse JSON response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            json_text = response_text.strip()

        try:
            parsed = json.loads(json_text)

            # Extract tags
            tags_data = parsed.get("tags", {})
            if isinstance(tags_data, dict) and "final_tags" in tags_data:
                llm_tags = [t for t in tags_data.get("final_tags", []) if isinstance(t, str)]
            else:
                llm_tags = [t for t in tags_data if isinstance(t, str)]

            # Extract workflow evaluation
            workflow_result = parsed.get("workflow", {})

            # Ensure required fields exist
            if "suggested_action" not in workflow_result:
                workflow_result["suggested_action"] = "proceed"
            if "clarification_questions" not in workflow_result:
                workflow_result["clarification_questions"] = []
            if "analysis_depth" not in workflow_result:
                workflow_result["analysis_depth"] = 1

        except json.JSONDecodeError:
            # Fallback to seed tags
            llm_tags = prompt_seed_tags
            workflow_result = {
                "complexity": "moderate",
                "confidence": 0.5,
                "reasoning": "JSON decode error",
                "needs_clarification": False,
                "needs_deep_analysis": False,
                "suggested_action": "proceed",
                "clarification_questions": [],
                "analysis_depth": 1
            }

    # Combine and normalize tags
    combined = normalize_tags(prompt_seed_tags + llm_tags, max_tags=6)
    combined = combined or prompt_seed_tags

    return {
        "tags": {
            "final_tags": combined,
            "seed_tags": prompt_seed_tags,
            "reasoning": tags_data.get("reasoning") if 'tags_data' in locals() else "Generated"
        },
        "workflow": workflow_result
    }


async def extract_keypoints(
    messages: list[dict], playbook: dict, diagnostic_name: str = "reflection", session_kpt_names: list[str] = None
) -> dict:
    """
    Extract key points from messages and evaluate existing playbook.

    Args:
        messages: Conversation messages to analyze
        playbook: Current playbook with existing key points
        diagnostic_name: Name for diagnostic logging
        session_kpt_names: Optional list of KPT names that were injected in this session.
                          If provided, only these KPTs will be evaluated for scoring.
                          Other KPTs will be preserved but not evaluated.
    """
    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for reflection", diagnostic_name)
        return {"new_key_points": [], "evaluations": []}

    template = load_template("reflection.txt")

    # Split key points based on whether they were injected this session
    session_kpt_names_set = set(session_kpt_names) if session_kpt_names else set()

    # All existing KPTs (for reference, not evaluation)
    existing_playbook = (
        {kp["name"]: kp["text"] for kp in playbook["key_points"] if not kp.get("pending")}
        if playbook["key_points"]
        else {}
    )

    # Only session KPTs should be evaluated for scoring
    # This filters existing_playbook to only include session-injected KPTs
    session_playbook_for_evaluation = (
        {kp["name"]: kp["text"] for kp in playbook["key_points"]
         if not kp.get("pending") and kp.get("name") in session_kpt_names_set}
        if playbook["key_points"]
        else {}
    )

    pending_playbook = (
        {kp["name"]: kp["text"] for kp in playbook["key_points"] if kp.get("pending")}
        if playbook["key_points"]
        else {}
    )

    # Collect existing tags from all key_points
    existing_tags = []
    if playbook and "key_points" in playbook:
        tags_set = set()
        for kp in playbook["key_points"]:
            kp_tags = kp.get("tags", [])
            if isinstance(kp_tags, list):
                tags_set.update(kp_tags)
        existing_tags = list(tags_set)

    existing_tags_context = f"\n\nExisting tags in playbook: {json.dumps(sorted(existing_tags))}"

    # Add session KPT information to the prompt
    session_context = ""
    if session_kpt_names:
        session_context = f"\n\n# Session-Injected Key Points for Evaluation\nThe following key points were injected during this session and should be evaluated for scoring: {json.dumps(session_kpt_names)}"

    prompt = template.format(
        trajectories=json.dumps(messages, indent=2, ensure_ascii=False),
        existing_playbook=json.dumps(
            session_playbook_for_evaluation if session_kpt_names else existing_playbook,
            indent=2,
            ensure_ascii=False
        ),
        pending_playbook=json.dumps(
            pending_playbook, indent=2, ensure_ascii=False
        ),
        existing_tags_context=existing_tags_context + session_context,
    )

    response = client.messages.create(
        model=model, max_tokens=4096, messages=[{"role": "user", "content": prompt}]
    )

    response_text_parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            response_text_parts.append(block.text)

    response_text = "".join(response_text_parts)

    if is_diagnostic_mode():
        save_diagnostic(
            f"# PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n",
            diagnostic_name,
        )

    if not response_text:
        return {"new_key_points": [], "evaluations": []}

    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        json_text = response_text[start:end].strip()
    else:
        json_text = response_text.strip()

    try:
        result = json.loads(json_text)
    except json.JSONDecodeError:
        return {"new_key_points": [], "evaluations": []}

    return {
        "merged_key_points": result.get("merged_key_points"),
        "new_key_points": result.get("new_key_points", []),
        "evaluations": result.get("evaluations", []),
    }
