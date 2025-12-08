"""Playbook management utilities."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

from utils import get_project_dir, get_user_claude_dir, is_diagnostic_mode, save_diagnostic


def validate_playbook_structure(data: dict) -> bool:
    """Validate that playbook has the expected structure."""
    required_keys = ["version", "key_points"]
    if not all(key in data for key in required_keys):
        return False

    if not isinstance(data["key_points"], list):
        return False

    for kp in data["key_points"]:
        if not isinstance(kp, dict):
            return False
        if "name" not in kp:
            return False

    return True


def load_playbook() -> dict:
    """Load the playbook JSON file."""
    project_dir = get_project_dir()
    playbook_path = project_dir / "playbook.json"

    if not playbook_path.exists():
        # Create initial playbook if it doesn't exist
        return {
            "version": "1.0",
            "key_points": [],
            "metadata": {"created_by": "Agentic Context Engineering", "last_updated": ""},
        }

    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            playbook = json.load(f)

        if not validate_playbook_structure(playbook):
            if is_diagnostic_mode():
                save_diagnostic("Invalid playbook structure", "playbook_load_error")
            return {
                "version": "1.0",
                "key_points": [],
                "metadata": {"error": "Invalid structure", "last_updated": ""},
            }

        return playbook
    except Exception as e:
        if is_diagnostic_mode():
            save_diagnostic(f"Failed to load playbook: {e}", "playbook_load_error")
        return {
            "version": "1.0",
            "key_points": [],
            "metadata": {"error": str(e), "last_updated": ""},
        }


def save_playbook(playbook: dict):
    """Save the playbook JSON file."""
    project_dir = get_project_dir()
    playbook_path = project_dir / "playbook.json"
    backup_path = project_dir / "playbook.json.backup"

    try:
        # Create backup of existing file
        if playbook_path.exists():
            playbook_path.rename(backup_path)

        # Add metadata
        playbook["metadata"] = playbook.get("metadata", {})
        playbook["metadata"]["last_updated"] = os.getenv("ACE_TIMESTAMP", "")

        # Save new version
        with open(playbook_path, "w", encoding="utf-8") as f:
            json.dump(playbook, f, indent=2, ensure_ascii=False)

    except Exception as e:
        # Restore from backup if available
        if backup_path.exists():
            backup_path.rename(playbook_path)
        raise e


def format_playbook(
    playbook: dict, key_points: Optional[list[dict]] = None, tags: Optional[list[str]] = None
) -> str:
    """Format playbook content for injection."""
    if not key_points:
        return ""

    context_parts = []

    # Add key points with improved formatting
    for kp in key_points:
        name = kp.get("name", "Unnamed")
        score = kp.get("score", 0)
        kp_tags = kp.get("tags", [])
        adjustable = kp.get("adjustable", True)

        # Skip non-adjustable key points if they shouldn't be modified
        if not adjustable:
            continue

        # Format score with sign
        score_str = f"+{score}" if score > 0 else str(score)
        tags_str = ", ".join(kp_tags) if kp_tags else "no tags"

        context_parts.append(f"• [{score_str}] {name} (tags: {tags_str})")

    return "\n".join(context_parts)


def update_playbook_data(playbook: dict, extraction_result: dict) -> dict:
    """Update playbook with extracted key points."""
    key_points = playbook.get("key_points", [])

    # Get existing names and tags
    existing_names = {kp["name"] for kp in key_points if isinstance(kp, dict)}
    all_existing_tags = set()
    for kp in key_points:
        if isinstance(kp, dict) and "tags" in kp:
            all_existing_tags.update(kp["tags"])

    # Process new key points
    new_keypoints = []
    for new_kp in extraction_result.get("key_points", []):
        if not isinstance(new_kp, dict):
            continue

        # Clean up the key point data
        cleaned_kp = {
            "name": new_kp.get("name", ""),
            "content": new_kp.get("content", ""),
            "score": int(new_kp.get("score", 0)),
            "tags": new_kp.get("tags", []),
            "adjustable": new_kp.get("adjustable", True),
        }

        # Generate unique name if needed
        if cleaned_kp["name"] in existing_names:
            cleaned_kp["name"] = generate_keypoint_name(existing_names)

        # Remove duplicate tags and normalize
        from tag_manager import normalize_tags
        cleaned_kp["tags"] = normalize_tags(cleaned_kp["tags"])

        # Update tracking
        existing_names.add(cleaned_kp["name"])
        all_existing_tags.update(cleaned_kp["tags"])
        new_keypoints.append(cleaned_kp)

    # Merge with existing key points
    updated_keypoints = key_points + new_keypoints

    # Update playbook structure
    updated_playbook = dict(playbook)
    updated_playbook["key_points"] = updated_keypoints

    # Update metadata
    metadata = updated_playbook.get("metadata", {})
    metadata["last_updated"] = os.getenv("ACE_TIMESTAMP", "")
    metadata["total_keypoints"] = len(updated_keypoints)
    updated_playbook["metadata"] = metadata

    return updated_playbook


def select_relevant_keypoints(
    playbook: dict,
    tags: list[str],
    limit: int = 6,
    prompt_tags: Optional[list[str]] = None,
    only_adjustable: bool = False
) -> list[dict]:
    """Simplified version: pick key points with exact tag matches only.

    Since LLM now handles similarity matching, we only need exact matching.
    """
    key_points = playbook.get("key_points", [])
    if not key_points:
        return []

    # Filter out non-adjustable key points if requested
    if only_adjustable:
        key_points = [kp for kp in key_points if kp.get("adjustable", True)]

    desired_tags = [t.lower() for t in tags or [] if isinstance(t, str)]

    # If no tags requested, return top scoring key points
    if not desired_tags:
        sorted_pool = sorted(
            key_points,
            key=lambda kp: (-kp.get("score", 0), kp.get("name", "")),
        )
        return sorted_pool[:limit]

    # Only return key points with exact tag matches
    matching = []
    for kp in key_points:
        kp_tags = [t.lower() for t in kp.get("tags", []) if isinstance(t, str)]

        # Check if any desired tag matches exactly
        if any(desired in kp_tags for desired in desired_tags):
            # Add simple match count for sorting
            kp = dict(kp)
            kp["_match_count"] = sum(1 for desired in desired_tags if desired in kp_tags)
            matching.append(kp)

    # If tags were requested but none matched, return empty
    if desired_tags and not matching:
        return []

    # Sort by match count, then by score
    sorted_pool = sorted(
        matching,
        key=lambda kp: (
            -kp.get("_match_count", 0),
            -kp.get("score", 0),
            kp.get("name", ""),
        ),
    )
    return sorted_pool[:limit]