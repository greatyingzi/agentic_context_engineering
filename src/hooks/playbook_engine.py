"""Playbook engine module for managing playbook data operations."""
import json
import sys
from typing import Optional


def generate_keypoint_name(existing_names: set) -> str:
    """Generate a unique keypoint name in the format 'kpt_XXX'.

    Args:
        existing_names: Set of existing keypoint names

    Returns:
        str: A unique keypoint name like 'kpt_001'
    """
    max_num = 0
    for name in existing_names:
        if name.startswith("kpt_"):
            try:
                num = int(name.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue

    return f"kpt_{max_num + 1:03d}"


def load_settings() -> dict:
    """Load settings from user's claude directory.

    Returns:
        dict: Settings dictionary with default values if file doesn't exist
    """
    try:
        from .utils.path_utils import get_user_claude_dir
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "utils"))
        from path_utils import get_user_claude_dir

    settings_path = get_user_claude_dir() / "settings.json"

    if not settings_path.exists():
        return {"playbook_update_on_exit": False, "playbook_update_on_clear": False}

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return {"playbook_update_on_exit": False, "playbook_update_on_clear": False}


def validate_playbook_structure(data: dict) -> bool:
    """Validate that playbook data has correct structure."""
    if not isinstance(data, dict):
        return False

    # Check required fields
    if 'key_points' in data and not isinstance(data['key_points'], list):
        return False

    # Check key_points structure if present
    if 'key_points' in data:
        for kp in data['key_points']:
            if isinstance(kp, dict):
                # Validate keypoint fields
                if 'text' in kp and not isinstance(kp['text'], str):
                    return False
                if 'tags' in kp and not isinstance(kp['tags'], list):
                    return False
                if 'score' in kp and not isinstance(kp['score'], (int, float)):
                    return False
                if 'name' in kp and not isinstance(kp['name'], str):
                    return False
                if 'pending' in kp and not isinstance(kp['pending'], bool):
                    return False

    return True


def load_playbook() -> dict:
    """Load playbook from project directory with validation and migration."""
    try:
        from .utils.path_utils import get_project_dir, is_diagnostic_mode, save_diagnostic
        from .utils.tag_utils import normalize_tags, infer_tags_from_text
    except ImportError:
        # Fallback for direct execution
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "utils"))
        from path_utils import get_project_dir, is_diagnostic_mode, save_diagnostic
        from tag_utils import normalize_tags, infer_tags_from_text
    import sys

    playbook_path = get_project_dir() / ".claude" / "playbook.json"

    if not playbook_path.exists():
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": []
        }

    def _is_divider(entry: object) -> bool:
        return isinstance(entry, dict) and entry.get("divider") is True

    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate playbook structure
        if not validate_playbook_structure(data):
            print(f"Warning: Invalid playbook structure in {playbook_path}, using default", file=sys.stderr)
            if is_diagnostic_mode():
                save_diagnostic(f"Invalid playbook structure in {playbook_path}", "playbook_validation")
            return {"version": "1.0", "last_updated": None, "key_points": []}

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

            keypoint["tags"] = normalize_tags(keypoint.get("tags", []))
            if not keypoint["tags"]:
                keypoint["tags"] = infer_tags_from_text(keypoint.get("text", ""))

            existing_names.add(keypoint["name"])
            keypoints.append(keypoint)

        data["key_points"] = keypoints
        return data

    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
        # Handle specific file-related errors
        print(f"Warning: Error loading playbook ({e}), using default", file=sys.stderr)
        if is_diagnostic_mode():
            save_diagnostic(f"Error loading playbook: {e}", "playbook_error")
        return {"version": "1.0", "last_updated": None, "key_points": []}
    except Exception:
        # Catch-all for any other unexpected errors
        return {"version": "1.0", "last_updated": None, "key_points": []}


def save_playbook(playbook: dict) -> bool:
    """Save playbook to file with atomic write and formatting.

    Returns:
        bool: True if save was successful, False otherwise
    """
    from datetime import datetime
    try:
        from .utils.path_utils import get_project_dir
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "utils"))
        from path_utils import get_project_dir

    playbook["last_updated"] = datetime.now().isoformat()
    playbook_path = get_project_dir() / ".claude" / "playbook.json"
    playbook_path.parent.mkdir(parents=True, exist_ok=True)

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

    serialized_keypoints = [_serialize_kp(kp) for kp in existing]
    if pending:
        serialized_keypoints.append(
            {
                "divider": True,
                "text": "--- pending key points below ---",
            }
        )
        serialized_keypoints.extend(_serialize_kp(kp, force_pending=True) for kp in pending)

    payload = dict(playbook)
    payload["key_points"] = serialized_keypoints

    # Atomic write: write to temp file first, then move
    temp_path = playbook_path.with_suffix('.tmp')
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        # Atomic move
        temp_path.replace(playbook_path)
        return True
    except Exception as e:
        # Clean up temp file if something goes wrong
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        # Return False instead of raising to allow caller to handle
        return False


def format_playbook(
    playbook: dict,
    key_points: Optional[list[dict]] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Format playbook content for display."""
    selected_key_points = key_points if key_points is not None else playbook.get("key_points", [])
    if not selected_key_points:
        return ""

    tags_text = ", ".join(tags) if tags else "all topics"
    key_points_text = "\n".join(
        f"- [score={kp.get('score', 0)}][tags={','.join(kp.get('tags', []))}] {kp.get('text', '')}"
        for kp in selected_key_points
        if isinstance(kp, dict)
    )

    try:
        from .file_utils import load_template
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from file_utils import load_template
    template = load_template("playbook.txt")
    return template.format(key_points=key_points_text, tags=tags_text)


def update_playbook_data(playbook: dict, extraction_result: dict) -> dict:
    """Update playbook with new key points and evaluations."""
    try:
        from .utils.tag_utils import normalize_tags, infer_tags_from_text
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / "utils"))
        from tag_utils import normalize_tags, infer_tags_from_text
    import re

    merged_key_points = extraction_result.get("merged_key_points")
    new_key_points = extraction_result.get("new_key_points", [])
    evaluations = extraction_result.get("evaluations", [])

    # Neutral should not penalize score; avoid drift toward deletion on repeated runs.
    rating_delta = {"helpful": 1, "harmful": -3, "neutral": 0}
    name_to_kp = {kp["name"]: kp for kp in playbook["key_points"]}

    # Apply evaluations first so scores are updated before merges.
    for eval_item in evaluations:
        name = eval_item.get("name", "")
        rating = eval_item.get("rating", "neutral")
        if name in name_to_kp:
            name_to_kp[name]["score"] += rating_delta.get(rating, 0)

    if merged_key_points is not None:
        # If model proposes fewer merged KPTs than existing ones, treat them as additions
        # instead of replacing the playbook to avoid accidental shrinking.
        if merged_key_points and len(merged_key_points) < len(playbook.get("key_points", [])):
            existing_names = {kp["name"] for kp in playbook["key_points"]}
            existing_texts = {kp.get("text", "") for kp in playbook["key_points"]}
            name_index = {kp["name"]: kp for kp in playbook["key_points"]}

            for item in merged_key_points:
                if isinstance(item, str):
                    text = item.strip()
                    tags = []
                    sources = []
                elif isinstance(item, dict):
                    text = (item.get("text") or "").strip()
                    tags = normalize_tags(item.get("tags", []))
                    sources = item.get("sources", []) or []
                else:
                    continue

                if not text or text in existing_texts:
                    continue

                source_kps = [name_index[s] for s in sources if s in name_index]
                total_score = sum(kp.get("score", 0) for kp in source_kps)
                fallback_tags = next(
                    (kp.get("tags", []) for kp in source_kps if kp.get("tags")), []
                )

                name = generate_keypoint_name(existing_names)
                playbook["key_points"].append(
                    {
                        "name": name,
                        "text": text,
                        "score": total_score,
                        "tags": tags or normalize_tags(fallback_tags) or infer_tags_from_text(text),
                        "pending": False,
                    }
                )
                existing_names.add(name)
                existing_texts.add(text)

        # Rebuild indices after any additions so downstream merge logic has mappings.
        existing_names = {kp["name"] for kp in playbook["key_points"]}
        text_index = {kp.get("text", ""): kp for kp in playbook["key_points"]}
        name_index = {kp["name"]: kp for kp in playbook["key_points"]}

        merged_list = []
        seen_texts = set()
        used_names = set()

        for item in merged_key_points or []:
            if isinstance(item, str):
                text = item.strip()
                tags = []
                sources = []
            elif isinstance(item, dict):
                text = (item.get("text") or "").strip()
                tags = normalize_tags(item.get("tags", []))
                sources = item.get("sources", []) or []
            else:
                continue

            if not text or text in seen_texts:
                continue

            matched_sources = []
            for source_name in sources:
                if source_name in name_index:
                    matched_sources.append(name_index[source_name])
                    used_names.add(source_name)

            source_kp = matched_sources[0] if matched_sources else text_index.get(text)

            if matched_sources:
                total_score = sum(kp.get("score", 0) for kp in matched_sources)
                fallback_tags = next((kp.get("tags", []) for kp in matched_sources if kp.get("tags")), [])
            elif source_kp:
                total_score = source_kp.get("score", 0)
                fallback_tags = source_kp.get("tags", [])
                used_names.add(source_kp["name"])
            else:
                total_score = 0
                fallback_tags = []

            name = source_kp["name"] if source_kp else generate_keypoint_name(existing_names)

            if any(kp.get("name") == name for kp in merged_list):
                name = generate_keypoint_name(existing_names)

            merged_list.append(
                {
                    "name": name,
                    "text": text,
                    "score": total_score,
                    "tags": tags or normalize_tags(fallback_tags) or infer_tags_from_text(text),
                    "pending": False,
                }
            )
            seen_texts.add(text)
            existing_names.add(name)

        # Preserve any existing items that were not part of the merged output.
        for kp in playbook.get("key_points", []):
            name = kp.get("name")
            text = kp.get("text", "")
            if name in used_names:
                continue
            if text in seen_texts:
                continue
            merged_list.append(kp)
            seen_texts.add(text)

        playbook["key_points"] = merged_list

    else:
        # Backward compatibility: treat returned new_key_points as pending additions.
        existing_names = {kp["name"] for kp in playbook["key_points"]}
        existing_texts = {kp["text"] for kp in playbook["key_points"]}

        for item in new_key_points:
            if isinstance(item, str):
                text = item
                tags = []
            elif isinstance(item, dict):
                text = item.get("text", "")
                tags = normalize_tags(item.get("tags", []))
            else:
                continue

            if not text or text in existing_texts:
                continue

            name = generate_keypoint_name(existing_names)
            playbook["key_points"].append(
                {
                    "name": name,
                    "text": text,
                    "score": 0,
                    "tags": tags or infer_tags_from_text(text),
                    "pending": True,
                }
            )
            existing_names.add(name)
            existing_texts.add(text)

    # Drop low-score items.
    playbook["key_points"] = [
        kp for kp in playbook["key_points"] if kp.get("score", 0) > -5
    ]

    # Enforce a hard cap by score to keep playbook size bounded.
    if len(playbook["key_points"]) > 250:
        playbook["key_points"] = sorted(
            playbook["key_points"],
            key=lambda kp: (-kp.get("score", 0), kp.get("name", "")),
        )[:250]

    # Renumber key points sequentially to keep identifiers compact.
    for idx, kp in enumerate(playbook["key_points"], start=1):
        kp["name"] = f"kpt_{idx:03d}"

    return playbook


def select_relevant_keypoints(
    playbook: dict, tags: list[str], limit: int = 6, prompt_tags: Optional[list[str]] = None
) -> list[dict]:
    """Pick highest scoring key points that match requested tags."""
    import re

    key_points = playbook.get("key_points", [])
    if not key_points:
        return []

    desired_tags = [t.lower() for t in tags or [] if isinstance(t, str)]
    prompt_tag_set = {t.lower() for t in (prompt_tags or [])}

    def tag_match_score(kp_tag: str, desired: str) -> int:
        """Exact =3, substring = 2, token overlap = 1, else 0."""
        if kp_tag == desired:
            return 3
        if kp_tag in desired or desired in kp_tag:
            return 2
        kp_tokens = set(re.split(r"[^a-z0-9]+", kp_tag))
        desired_tokens = set(re.split(r"[^a-z0-9]+", desired))
        kp_tokens.discard("")
        desired_tokens.discard("")
        return 1 if kp_tokens & desired_tokens else 0

    def score_and_coverage(kp_tags: list[str]) -> tuple[int, int, int]:
        best = 0
        matched = set()
        prompt_hits = 0
        for kp_tag in kp_tags:
            kp_norm = kp_tag.lower()
            for desired in desired_tags:
                s = tag_match_score(kp_norm, desired)
                if s > 0:
                    matched.add(desired)
                    if desired in prompt_tag_set:
                        prompt_hits += 1
                    best = max(best, s)
                    if best == 3 and len(matched) == len(desired_tags):
                        return best, len(matched), prompt_hits
        return best, len(matched), prompt_hits

    matching = []
    if desired_tags:
        for kp in key_points:
            kp_tags = [t for t in kp.get("tags", []) if isinstance(t, str)]
            score, coverage, prompt_hits = score_and_coverage(kp_tags)
            if score > 0 and coverage > 0:
                kp = dict(kp)
                kp["_match_score"] = score
                kp["_match_coverage"] = coverage
                kp["_prompt_hits"] = prompt_hits
                kp["_total_match"] = (
                    10 * coverage
                    + 3 * score
                    + 5 * prompt_hits
                    + kp.get("score", 0)
                )
                matching.append(kp)

    # If tags were requested but none matched even fuzzily, return empty to avoid unrelated injection.
    if desired_tags and not matching:
        return []

    pool = matching if matching else key_points

    sorted_pool = sorted(
        pool,
        key=lambda kp: (
            -kp.get("_total_match", 0),
            -kp.get("_match_coverage", 0),
            -kp.get("_match_score", 0),
            -kp.get("_prompt_hits", 0),
            -kp.get("score", 0),
            kp.get("name", ""),
        ),
    )
    return sorted_pool[:limit]