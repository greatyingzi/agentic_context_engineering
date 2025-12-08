"""Playbook management utilities."""

import json
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any

from utils import get_project_dir, get_user_claude_dir, is_diagnostic_mode, save_diagnostic
from llm_client import generate_keypoint_name

MAX_KEYPOINTS = 250


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
    playbook_path = project_dir / ".claude" / "playbook.json"

    # Ensure .claude directory exists
    playbook_path.parent.mkdir(parents=True, exist_ok=True)

    if not playbook_path.exists():
        # Create initial playbook if it doesn't exist
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": [],
            "metadata": {"created_by": "Agentic Context Engineering", "last_updated": ""},
        }

    def _is_divider(entry: object) -> bool:
        return isinstance(entry, dict) and entry.get("divider") is True

    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not validate_playbook_structure(data):
            if is_diagnostic_mode():
                save_diagnostic("Invalid playbook structure", "playbook_load_error")
            return {
                "version": "1.0",
                "last_updated": None,
                "key_points": [],
                "metadata": {"error": "Invalid structure", "last_updated": ""},
            }

        if "key_points" not in data:
            data["key_points"] = []

        keypoints = []
        existing_names = set()

        for item in data["key_points"]:
            if _is_divider(item):
                continue
            if isinstance(item, str):
                keypoint = {
                    "name": generate_keypoint_name(existing_names),
                    "text": item,
                    "score": 0,
                    "pending": False,
                }
            elif isinstance(item, dict):
                keypoint = dict(item)
                if "name" not in keypoint:
                    keypoint["name"] = generate_keypoint_name(existing_names)
                if "score" not in keypoint:
                    keypoint["score"] = 0
                if "pending" not in keypoint:
                    keypoint["pending"] = False
            else:
                continue

            # Normalize tags and infer if missing
            from tag_manager import normalize_tags
            from llm_client import infer_tags_from_text
            keypoint["tags"] = normalize_tags(keypoint.get("tags", []))
            if not keypoint["tags"]:
                keypoint["tags"] = infer_tags_from_text(keypoint.get("text", ""))

            existing_names.add(keypoint["name"])
            keypoints.append(keypoint)

        data["key_points"] = keypoints
        return data
    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
        if is_diagnostic_mode():
            save_diagnostic(f"Failed to load playbook: {e}", "playbook_load_error")
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": [],
            "metadata": {"error": str(e), "last_updated": ""},
        }
    except Exception:
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": [],
            "metadata": {"error": "Unknown error", "last_updated": ""},
        }


def save_playbook(playbook: dict):
    """Save the playbook JSON file with enhanced error handling and logging."""
    project_dir = get_project_dir()
    playbook_path = project_dir / ".claude" / "playbook.json"
    backup_path = project_dir / ".claude" / "playbook.json.backup"

    # Ensure .claude directory exists
    try:
        playbook_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error_msg = f"Failed to create .claude directory: {e}"
        if is_diagnostic_mode():
            save_diagnostic(error_msg, "playbook_save_error")
        raise Exception(error_msg)

    backup_created = False

    try:
        # Create backup of existing file (use copy2 to avoid permission issues)
        if playbook_path.exists():
            try:
                shutil.copy2(playbook_path, backup_path)
                backup_created = True
                if is_diagnostic_mode():
                    save_diagnostic(f"Created backup at {backup_path}", "playbook_save_info")
            except Exception as e:
                error_msg = f"Failed to create backup: {e}"
                if is_diagnostic_mode():
                    save_diagnostic(error_msg, "playbook_save_warning")
                # Continue without backup but log the issue

        # Add metadata
        playbook["metadata"] = playbook.get("metadata", {})
        playbook["metadata"]["last_updated"] = os.getenv("ACE_TIMESTAMP", "")

        # Insert a visual divider between stable items and pending ones for readability.
        existing = [kp for kp in playbook.get("key_points", []) if not kp.get("pending")]
        pending = [kp for kp in playbook.get("key_points", []) if kp.get("pending")]

        def _serialize_kp(kp: dict, force_pending: bool = False) -> dict:
            item = dict(kp)
            is_pending = bool(item.get("pending")) or force_pending
            if is_pending:
                item["pending"] = True
            else:
                item.pop("pending", None)
            return item

        try:
            serialized_keypoints = [_serialize_kp(kp) for kp in existing]
            if pending:
                serialized_keypoints.append(
                    {
                        "divider": True,
                        "text": "--- pending key points below ---",
                    }
                )
                serialized_keypoints.extend(_serialize_kp(kp, force_pending=True) for kp in pending)
        except Exception as e:
            error_msg = f"Failed to serialize keypoints: {e}"
            if is_diagnostic_mode():
                save_diagnostic(error_msg, "playbook_save_error")
            raise Exception(error_msg)

        # Save with proper key_points structure
        save_data = dict(playbook)
        save_data["key_points"] = serialized_keypoints

        # Save new version
        try:
            with open(playbook_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            error_msg = f"Failed to write playbook to {playbook_path}: {e}"
            if is_diagnostic_mode():
                save_diagnostic(error_msg, "playbook_save_error")
            raise Exception(error_msg)

        # Success log
        if is_diagnostic_mode():
            total_kps = len(existing) + len(pending)
            save_diagnostic(
                f"Successfully saved playbook with {total_kps} keypoints ({len(existing)} stable, {len(pending)} pending)",
                "playbook_save_success"
            )

    except Exception as e:
        # Restore from backup if available
        if backup_created and backup_path.exists():
            try:
                shutil.copy2(backup_path, playbook_path)
                if is_diagnostic_mode():
                    save_diagnostic("Restored backup after save failure", "playbook_save_recovery")
            except Exception as restore_error:
                error_msg = f"Critical: Failed to restore backup after save failure: {restore_error}"
                if is_diagnostic_mode():
                    save_diagnostic(error_msg, "playbook_save_critical")

        # Re-raise the original exception with context
        raise Exception(f"Playbook save failed: {e}") from e


def format_playbook(
    playbook: dict, key_points: Optional[list[dict]] = None
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

        # Include keypoint text content
        text = kp.get("text", "")
        if text:
            context_parts.append(f"• [{score_str}] {name} (tags: {tags_str}) {text}")
        else:
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

    # First apply score changes if present
    score_changes = extraction_result.get("score_changes", [])
    for change in score_changes:
        if not isinstance(change, dict):
            continue
        name = change.get("name")
        rating = change.get("rating")
        if name is not None and rating is not None:
            # Convert rating to score change
            score_change = 0
            if rating == "helpful":
                score_change = 1
            elif rating == "harmful":
                score_change = -3
            # "neutral" scores are 0 and don't need to be applied

            if score_change != 0:
                # Find and update the keypoint with this name
                for kp in key_points:
                    if isinstance(kp, dict) and kp.get("name") == name:
                        current_score = kp.get("score", 0)
                        kp["score"] = current_score + score_change
                        break

    # Process new key points
    new_keypoints = []
    for new_kp in extraction_result.get("merged_key_points", []):
        if not isinstance(new_kp, dict):
            continue

        # Clean up the key point data
        cleaned_kp = {
            "name": new_kp.get("name", ""),
            "text": new_kp.get("text", ""),
            "score": int(new_kp.get("score", 0)),
            "tags": new_kp.get("tags", []),
            "adjustable": new_kp.get("adjustable", True),
        }

        # Generate unique name if needed
        if not cleaned_kp["name"] or cleaned_kp["name"] in existing_names:
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

    # Enforce MAX_KEYPOINTS limit - keep highest scoring ones
    if len(updated_keypoints) > MAX_KEYPOINTS:
        sorted_keypoints = sorted(
            updated_keypoints,
            key=lambda kp: (kp.get("score", 0), kp.get("name", "")),
            reverse=True
        )
        updated_keypoints = sorted_keypoints[:MAX_KEYPOINTS]

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
    only_adjustable: bool = False
) -> list[dict]:
    """Select key points that match requested tags.

    Returns key points with exact tag matches only, sorted by:
    1. Number of matching tags (more matches first)
    2. Key point score (higher score first)
    3. Key point name (alphabetical)
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