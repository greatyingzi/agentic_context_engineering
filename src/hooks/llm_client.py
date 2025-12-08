"""LLM client utilities."""

import json
import os
from typing import List, Optional, Tuple

# For LLM client
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def get_anthropic_client() -> Tuple[Optional["anthropic.Anthropic"], Optional[str]]:
    """Return (client, model). If diagnostics are on, log why a client is missing."""
    if not ANTHROPIC_AVAILABLE:
        from utils import save_diagnostic, is_diagnostic_mode
        if is_diagnostic_mode():
            save_diagnostic("anthropic not installed", "client_missing")
        return None, None

    model = (
        os.getenv("AGENTIC_CONTEXT_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or "claude-3-5-sonnet-20241022"
    )
    api_key = (
        os.getenv("AGENTIC_CONTEXT_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        from utils import save_diagnostic, is_diagnostic_mode
        if is_diagnostic_mode():
            save_diagnostic(
                "Neither AGENTIC_CONTEXT_API_KEY nor ANTHROPIC_API_KEY is set",
                "client_missing"
            )
        return None, None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        return client, model
    except Exception as e:
        from utils import save_diagnostic, is_diagnostic_mode
        if is_diagnostic_mode():
            save_diagnostic(f"Failed to create client: {e}", "client_missing")
        return None, None


def generate_tags_from_messages(
    messages: List[dict],
    prompt_text: str = "",
    playbook: Optional[dict] = None,
    diagnostic_name: str = "tagger"
) -> Tuple[List[str], List[str]]:
    """Generate request tags from recent conversation history and pending prompt.

    Args:
        messages: Recent conversation history
        prompt_text: The current prompt text
        playbook: Optional playbook containing existing tags for recommendations
        diagnostic_name: Name for diagnostic logging

    Returns:
        Tuple of (final_tags, seed_tags)
    """
    from utils import save_diagnostic, is_diagnostic_mode, load_template
    from tag_manager import normalize_tags

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
        return [], []

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
        return [], []

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

        # Handle both array format (["tag1", "tag2"]) and object format ({"tags": ["tag1", "tag2"]})
        if isinstance(parsed, list):
            # Direct array response from template
            final_tags = normalize_tags(parsed)
        elif isinstance(parsed, dict):
            # Object response with tags field
            final_tags = normalize_tags(parsed.get("tags", []))
        else:
            # Unexpected format
            final_tags = normalize_tags([])

        return final_tags, final_tags
    except (json.JSONDecodeError, AttributeError) as e:
        # Return empty tags if JSON parsing fails
        if is_diagnostic_mode():
            save_diagnostic(f"JSON parsing error in generate_tags_from_messages: {e}\nResponse: {response_text[:200]}...", "tagger_error")
        return [], []


def infer_tags_from_text(text: str, max_tags: int = 5) -> list[str]:
    """Simple rule-based tag inference from text."""
    if not text:
        return []

    # Enhanced keyword mapping that includes existing playbook tags
    tech_terms = {
        "bug": ["bug", "error", "issue", "problem", "fix", "debug"],
        "feature": ["feature", "add", "implement", "create", "new"],
        "refactor": ["refactor", "cleanup", "improve", "optimize"],
        "test": ["test", "testing", "unit test", "coverage", "verification"],
        "api": ["api", "endpoint", "route", "controller"],
        "ui": ["ui", "frontend", "interface", "component", "user-interface"],
        "database": ["database", "db", "sql", "query"],
        "config": ["config", "settings", "environment"],
        "deploy": ["deploy", "deployment", "release"],
        "security": ["security", "auth", "authentication", "permission", "vulnerability"],
        # Existing playbook tags
        "documentation": ["documentation", "docs", "readme", "guide"],
        "analysis": ["analysis", "analyze", "review", "examine"],
        "accuracy": ["accuracy", "correctness", "precision"],
        "i18n": ["i18n", "international", "localization", "locale", "translation"],
        "sync": ["sync", "synchronization", "synchronize"],
        "updates": ["updates", "update", "upgrade"],
        "maintenance": ["maintenance", "maintain", "upkeep"],
        "performance": ["performance", "optimize", "speed", "fast", "slow"],
        "metrics": ["metrics", "measurement", "monitoring"],
        "git": ["git", "commit", "branch", "merge", "repository"],
        "workflow": ["workflow", "process", "pipeline"],
        "architecture": ["architecture", "design", "structure"],
        "error-handling": ["error", "exception", "handling", "try", "catch"],
        "user-guidance": ["guidance", "help", "instruction"],
        "guidance": ["guidance", "help", "instruction"],
        "features": ["features", "capability", "functionality"],
        "timeliness": ["timeliness", "time", "deadline", "schedule"],
        "playbook": ["playbook", "play", "save"],
        "save": ["save", "store", "persist"],
    }

    text_lower = text.lower()
    found_tags = []

    for category, keywords in tech_terms.items():
        if any(keyword in text_lower for keyword in keywords):
            found_tags.append(category)
            if len(found_tags) >= max_tags:
                break

    return found_tags


def generate_keypoint_name(existing_names: set) -> str:
    """Generate a unique keypoint name in kpt_001 format."""
    max_num = 0
    for name in existing_names:
        if name.startswith("kpt_"):
            try:
                num = int(name.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue
    return f"kpt_{max_num + 1:03d}"


async def extract_keypoints(
    messages: list[dict], playbook: dict, diagnostic_name: str = "reflection"
) -> dict:
    """Extract key points from conversation history using LLM."""
    from utils import save_diagnostic, is_diagnostic_mode, load_template

    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for reflection", diagnostic_name)
        return {"new_key_points": [], "score_changes": []}

    template = load_template("reflection.txt")

    existing_playbook = (
        {kp["name"]: kp["text"] for kp in playbook["key_points"] if not kp.get("pending")}
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

    prompt = template.format(
        trajectories=json.dumps(messages, indent=2, ensure_ascii=False),
        existing_playbook=json.dumps(
            existing_playbook, indent=2, ensure_ascii=False
        ),
        pending_playbook=json.dumps(
            pending_playbook, indent=2, ensure_ascii=False
        ),
        existing_tags_context=existing_tags_context,
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
        return {"new_key_points": [], "score_changes": []}

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
        return {"new_key_points": [], "score_changes": []}

    return {
        "merged_key_points": result.get("merged_key_points"),
        "new_key_points": result.get("new_key_points", []),
        "score_changes": result.get("score_changes", []),
    }