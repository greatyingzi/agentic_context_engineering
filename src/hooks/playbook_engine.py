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

                # Phase 2 Emergency Fix: Validate multi-dimensional fields
                if 'effect_rating' in kp and not isinstance(kp['effect_rating'], (int, float)):
                    return False
                if 'effect_rating' in kp and not (0 <= kp['effect_rating'] <= 1):
                    return False
                if 'risk_level' in kp and not isinstance(kp['risk_level'], (int, float)):
                    return False
                # Risk is intentionally a signed score where positives mean higher risk.
                if 'risk_level' in kp and not (-1 <= kp['risk_level'] <= 1):
                    return False
                if 'innovation_level' in kp and not isinstance(kp['innovation_level'], (int, float)):
                    return False
                if 'innovation_level' in kp and not (0 <= kp['innovation_level'] <= 1):
                    return False

    return True


def load_playbook() -> dict:
    """Load playbook with intelligent migration and version control."""
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
                    # Phase 2 Emergency Fix: Add multi-dimensional defaults for existing KPTs
                    "effect_rating": _infer_effect_rating_from_score(0),
                    "risk_level": _infer_risk_level_from_text(item),
                    "innovation_level": _infer_innovation_from_text(item),
                }
            elif isinstance(item, dict):
                keypoint = dict(item)
                if "name" not in keypoint:
                    keypoint["name"] = generate_keypoint_name(existing_names)
                if "score" not in keypoint:
                    keypoint["score"] = 0
                if "pending" not in keypoint:
                    keypoint["pending"] = False

                # Phase 2 Emergency Fix: Ensure multi-dimensional fields exist for existing KPTs
                if "effect_rating" not in keypoint:
                    keypoint["effect_rating"] = _infer_effect_rating_from_score(keypoint.get("score", 0))
                if "risk_level" not in keypoint:
                    keypoint["risk_level"] = _infer_risk_level_from_score_and_tags(keypoint)
                if "innovation_level" not in keypoint:
                    keypoint["innovation_level"] = _infer_innovation_from_tags(keypoint.get("tags", []))
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
        """Serialize a keypoint with enhanced field validation for multi-dimensional data."""
        item = dict(kp)  # 浅拷贝所有字段，包括新字段

        is_pending = bool(item.get("pending")) or force_pending
        if is_pending:
            item["pending"] = True
        else:
            item.pop("pending", None)

        # Phase 2 Emergency Fix: Validate multi-dimensional fields
        # 确保新字段存在且类型正确
        if "effect_rating" not in item:
            item["effect_rating"] = 0.5  # 默认中等效果
        elif not isinstance(item["effect_rating"], (int, float)) or not (0 <= item["effect_rating"] <= 1):
            # 如果值无效，重置为默认值
            item["effect_rating"] = 0.5

        if "risk_level" not in item:
            item["risk_level"] = -0.5  # 默认中等风险
        elif not isinstance(item["risk_level"], (int, float)) or not (-1 <= item["risk_level"] <= 1):
            # 如果值无效，重置为默认值
            item["risk_level"] = -0.5

        if "innovation_level" not in item:
            item["innovation_level"] = 0.5  # 默认中等创新
        elif not isinstance(item["innovation_level"], (int, float)) or not (0 <= item["innovation_level"] <= 1):
            # 如果值无效，重置为默认值
            item["innovation_level"] = 0.5

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

    # Enhanced 7-level rating system for more granular feedback
    rating_delta = {
        "highly_effective": 3,
        "moderately_useful": 2,
        "slightly_useful": 1,
        "neutral": 0,
        "slightly_harmful": -1,
        "moderately_harmful": -2,
        "highly_dangerous": -4
    }
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

            # Extract multi-dimensional assessment for new key points
            effect_rating = item.get("effect_rating", 0.5) if isinstance(item, dict) else 0.5
            risk_level = item.get("risk_level", -0.5) if isinstance(item, dict) else -0.5
            innovation_level = item.get("innovation_level", 0.5) if isinstance(item, dict) else 0.5

            playbook["key_points"].append(
                {
                    "name": name,
                    "text": text,
                    "score": 0,
                    "tags": tags or infer_tags_from_text(text),
                    "pending": True,
                    "effect_rating": effect_rating,
                    "risk_level": risk_level,
                    "innovation_level": innovation_level,
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
    playbook: dict, tags: list[str], limit: int = 6, prompt_tags: Optional[list[str]] = None, temperature: float = 0.5
) -> list[dict]:
    """TRUE dual-layer classification with clear boundaries.

    Layer 1: High-Confidence Matching (score >= 2)
    Layer 2: Recommendation-Based (0 <= score < 2)

    Temperature determines allocation between layers:
    - Conservative (0.1-0.3): 70% Layer 1, 30% Layer 2
    - Balanced (0.4-0.6): 50% each layer
    - Exploratory (0.7-1.0): 30% Layer 1, 70% Layer 2
    """
    import re

    key_points = playbook.get("key_points", [])
    if not key_points:
        return []

    desired_tags = [t.lower() for t in tags or [] if isinstance(t, str)]
    prompt_tag_set = {t.lower() for t in (prompt_tags or [])}

    # Create text for context analysis
    all_tags_text = " ".join(desired_tags).lower()

    # Define clear classification boundaries
    HIGH_CONFIDENCE_THRESHOLD = 2.0

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

    # CLASSIFICATION PHASE: Separate into two distinct layers
    high_confidence_layer = []  # Layer 1: score >= 2
    recommendation_layer = []    # Layer 2: 0 <= score < 2

    for kp in key_points:
        kp_tags = [t for t in kp.get("tags", []) if isinstance(t, str)]
        score, coverage, prompt_hits = score_and_coverage(kp_tags)

        # Skip negative scoring items entirely
        kp_score = kp.get("score", 0)
        if kp_score < 0:
            continue

        if score > 0 and coverage > 0:
            # Calculate base weight
            base_weight = 10 * coverage + 3 * score + 5 * prompt_hits + kp_score

            # LAYER-SPECIFIC TEMPERATURE APPLICATION
            if kp_score >= HIGH_CONFIDENCE_THRESHOLD:
                # LAYER 1: High-Confidence Matching
                layer_type = "HIGH_CONFIDENCE"

                # Temperature affects high-confidence items INVERSELY
                # Low temperature = HIGH weight for proven solutions
                temp_multiplier = 2.5 - temperature * 1.5

                # Additional layer-specific adjustments
                if temperature <= 0.3:
                    temp_multiplier += 0.5  # Conservative boost for proven items
                elif temperature >= 0.7:
                    temp_multiplier -= 0.3  # Exploratory mode reduces proven item weight

            else:
                # LAYER 2: Recommendation-Based
                layer_type = "RECOMMENDATION"

                # Temperature affects recommendation items DIRECTLY
                # High temperature = HIGH weight for exploration
                temp_multiplier = temperature * 2.0

                # Additional layer-specific adjustments
                if temperature <= 0.3:
                    temp_multiplier *= 0.3  # Conservative suppresses recommendations
                elif temperature >= 0.7:
                    temp_multiplier += 0.5  # Exploratory boosts recommendations

            # Apply multi-dimensional adjustments
            effect_rating = kp.get("effect_rating", 0.5)
            risk_level = kp.get("risk_level", -0.5)
            innovation_level = kp.get("innovation_level", 0.5)

            # Context-aware parameter weights
            effect_weight, innovation_weight, risk_threshold = _get_contextual_weights(
                layer_type, all_tags_text
            )

            if layer_type == "HIGH_CONFIDENCE":
                # High confidence items get effectiveness boost
                temp_multiplier += effect_rating * effect_weight
                # Risk reduction for proven items
                if risk_level < risk_threshold:
                    temp_multiplier += 0.2
            else:
                # Recommendations get innovation boost
                temp_multiplier += innovation_level * innovation_weight
                # Risk awareness for new ideas
                if risk_level > risk_threshold:
                    temp_multiplier *= 0.8

            # Store metadata for debugging
            kp["_layer"] = layer_type
            kp["_base_weight"] = base_weight
            kp["_temp_multiplier"] = temp_multiplier
            kp["_total_match"] = base_weight * temp_multiplier
            kp["_match_score"] = score
            kp["_match_coverage"] = coverage
            kp["_prompt_hits"] = prompt_hits

            # CLASSIFY INTO CORRECT LAYER
            if layer_type == "HIGH_CONFIDENCE":
                high_confidence_layer.append(kp)
            else:
                recommendation_layer.append(kp)

    # TEMPERATURE-BASED ALLOCATION PHASE
    if temperature <= 0.3:
        # CONSERVATIVE: Prioritize proven solutions
        high_confidence_limit = max(4, int(limit * 0.7))  # Up to 70%
        recommendation_limit = max(1, limit - high_confidence_limit)  # At least 1
    elif temperature >= 0.7:
        # EXPLORATORY: Prioritize new ideas
        recommendation_limit = max(4, int(limit * 0.7))  # Up to 70%
        high_confidence_limit = max(1, limit - recommendation_limit)  # At least 1
    else:
        # BALANCED: Equal allocation
        high_confidence_limit = limit // 2
        recommendation_limit = limit - high_confidence_limit

    # Sort each layer internally
    sorted_high_confidence = sorted(high_confidence_layer, key=lambda kp: -kp["_total_match"])[:high_confidence_limit]
    sorted_recommendations = sorted(recommendation_layer, key=lambda kp: -kp["_total_match"])[:recommendation_limit]

    # MERGE WITH LAYER PRIORITY
    final_selection = []

    # Layer-specific ranking
    for i, kp in enumerate(sorted_high_confidence):
        kp["_layer_rank"] = f"HC-{i+1}"
        final_selection.append(kp)

    for i, kp in enumerate(sorted_recommendations):
        kp["_layer_rank"] = f"RC-{i+1}"
        final_selection.append(kp)

    # FINAL SORTING: Temperature-aware global ordering
    if temperature <= 0.3:
        # Conservative: High confidence items first
        final_selection = sorted(final_selection, key=lambda kp: (
            0 if kp["_layer"] == "HIGH_CONFIDENCE" else 2,  # HC first
            1 if kp["_layer"] == "RECOMMENDATION" else 3,  # RC second
            -kp["_total_match"]  # Then by score
        ))
    elif temperature >= 0.7:
        # Exploratory: Recommendations first
        final_selection = sorted(final_selection, key=lambda kp: (
            0 if kp["_layer"] == "RECOMMENDATION" else 2,  # RC first
            1 if kp["_layer"] == "HIGH_CONFIDENCE" else 3,  # HC second
            -kp["_total_match"]  # Then by score
        ))
    else:
        # Balanced: Mix by score but preserve layer identity
        final_selection = sorted(final_selection, key=lambda kp: -kp["_total_match"])

    # Return only the requested limit
    return final_selection[:limit]

def apply_intelligent_filtering(kps: list[dict], temperature: float, limit: int) -> list[dict]:
    """Phase 3: Intelligent filtering to ensure diversity and safety"""

    # 1. Extreme risk filtering
    filtered_kps = []
    extreme_risk_threshold = 0.8 if temperature <= 0.4 else 0.6

    for kp in kps:
        risk_level = kp.get("risk_level", -0.5)

        # Filter extremely risky items based on temperature
        if temperature <= 0.2 and risk_level > extreme_risk_threshold:
            # In very conservative mode, filter extremely risky items
            continue
        elif temperature <= 0.5 and risk_level > 0.8:
            # In balanced mode, filter reckless items
            continue
        elif risk_level > 0.9:
            # Always filter reckless items in any mode
            continue

        filtered_kps.append(kp)

    # 2. Diversity preservation - prevent single-source dominance
    if len(filtered_kps) > limit * 2:
        tag_counts = {}
        diverse_kps = []

        for kp in filtered_kps:
            primary_tag = get_primary_tag(kp.get("tags", []))

            if tag_counts.get(primary_tag, 0) < limit // 2:
                diverse_kps.append(kp)
                tag_counts[primary_tag] = tag_counts.get(primary_tag, 0) + 1
            elif temperature > 0.7:  # In exploratory mode, be more permissive
                tag_counts[primary_tag] = tag_counts.get(primary_tag, 0) + 1
                diverse_kps.append(kp)

        filtered_kps = diverse_kps

    # 3. Quality filtering for conservative modes
    if temperature <= 0.3:
        # In conservative mode, filter out low-effectiveness items
        min_effectiveness = 0.3
        filtered_kps = [
            kp for kp in filtered_kps
            if kp.get("effect_rating", 0.5) >= min_effectiveness
        ]

    return filtered_kps


def _get_contextual_weights(layer_type: str, all_tags_text: str) -> tuple[float, float, float]:
    """
    Get context-aware parameter weights based on detected context patterns.

    Returns:
        (effect_weight, innovation_weight, risk_threshold)
    """
    # Context detection patterns
    urgent_indicators = ["fix", "bug", "error", "urgent", "critical", "broken"]
    exploratory_indicators = ["explore", "learn", "research", "alternative", "innovative", "prototype", "experimental"]
    production_indicators = ["production", "deploy", "release", "customer", "enterprise", "stable"]

    # Detect contexts
    urgent_context = any(indicator in all_tags_text for indicator in urgent_indicators)
    exploratory_context = any(indicator in all_tags_text for indicator in exploratory_indicators)
    production_context = any(indicator in all_tags_text for indicator in production_indicators)

    # Default weights
    default_effect_weight = 0.3
    default_innovation_weight = 0.4
    default_risk_threshold = -0.2

    # Context-aware weight adjustments
    if urgent_context:
        # Urgent contexts prioritize proven effectiveness
        if layer_type == "HIGH_CONFIDENCE":
            return 0.5, 0.1, -0.3  # Heavy on effectiveness, very low risk tolerance
        else:
            return 0.2, 0.2, -0.6  # Favor proven solutions, extremely risk-averse

    elif production_context:
        # Production contexts balance effectiveness and innovation
        if layer_type == "HIGH_CONFIDENCE":
            return 0.4, 0.2, -0.4  # Emphasize proven effectiveness
        else:
            return 0.3, 0.3, -0.3  # Balanced but cautious

    elif exploratory_context:
        # Exploratory contexts prioritize innovation
        if layer_type == "HIGH_CONFIDENCE":
            return 0.2, 0.4, -0.1  # Less emphasis on past effectiveness
        else:
            return 0.1, 0.6, 0.2   # Strong innovation focus, risk-tolerant

    else:
        # Default balanced approach
        return default_effect_weight, default_innovation_weight, default_risk_threshold


def apply_adaptive_optimization(kps: list[dict], temperature: float, desired_tags: list[str]) -> list[dict]:
    """Phase 3: Adaptive optimization based on context"""

    # Contextual temperature adjustment based on tag analysis
    if not desired_tags:
        return kps

    # Analyze request characteristics for adaptive adjustment
    urgent_indicators = ["fix", "bug", "error", "urgent", "critical", "broken"]
    exploratory_indicators = ["explore", "learn", "research", "alternative", "innovative"]
    production_indicators = ["production", "deploy", "release", "customer", "enterprise"]

    all_tags_text = " ".join(desired_tags).lower()

    # Adaptive temperature adjustment
    adjusted_temperature = temperature

    # Detect context patterns
    urgent_context = any(indicator in all_tags_text for indicator in urgent_indicators)
    exploratory_context = any(indicator in all_tags_text for indicator in exploratory_indicators)
    production_context = any(indicator in all_tags_text for indicator in production_indicators)

    # Apply contextual adjustments
    if urgent_context and temperature > 0.3:
        adjusted_temperature = min(temperature - 0.4, 0.3)  # Force conservative
    elif production_context and temperature > 0.5:
        adjusted_temperature = min(temperature - 0.2, 0.5)  # Moderate adjustment
    elif exploratory_context and temperature < 0.7:
        adjusted_temperature = max(temperature + 0.3, 0.7)  # Encourage exploration

    # Recalculate weights with adjusted temperature
    for kp in kps:
        base_weight = kp.get("_total_match", 0)

        # Apply adaptive multiplier
        if adjusted_temperature != temperature:
            # Recalculate weight with adjusted temperature
            old_temp_multiplier = kp.get("_temp_multiplier", 1.0)

            # Simple approximation of temperature effect
            temp_ratio = adjusted_temperature / temperature
            adaptive_multiplier = old_temp_multiplier * temp_ratio

            kp["_total_match"] = base_weight * temp_ratio
            kp["_adaptive_multiplier"] = adaptive_multiplier
            kp["_adjusted_temperature"] = adjusted_temperature

    return kps

def get_primary_tag(tags: list[str]) -> str:
    """Get the primary tag for diversity filtering"""
    if not tags:
        return "unknown"

    # Priority order for primary tag selection
    tech_tags = ["python", "javascript", "react", "node", "api", "database", "sql", "git", "docker"]
    action_tags = ["testing", "deployment", "error-handling", "security", "performance", "optimization"]

    # Check for high-priority tags
    for tag in tags:
        if tag in tech_tags:
            return tag
        if tag in action_tags:
            return tag

    # Fallback to first tag
    return tags[0].lower()


def _infer_effect_rating_from_score(score: int) -> float:
    """Phase 2 Emergency Fix: Infer effect_rating from historical score"""
    if score >= 3:
        return 0.9  # 历史高效，高效果
    elif score >= 1:
        return 0.6  # 中等效果
    elif score >= 0:
        return 0.4  # 基础效果
    else:
        return 0.2  # 效果不佳


def _infer_risk_level_from_text(text: str) -> float:
    """Phase 2 Emergency Fix: Infer risk_level from text content"""
    text_lower = text.lower()

    # 高风险关键词
    high_risk_keywords = ["experimental", "cutting-edge", "unstable", "beta", "risky", "dangerous", "hack"]
    medium_risk_keywords = ["new", "alternative", "innovative", "advanced"]
    safe_keywords = ["standard", "proven", "stable", "tested", "safe", "reliable"]

    if any(keyword in text_lower for keyword in high_risk_keywords):
        return 0.2  # 高风险
    elif any(keyword in text_lower for keyword in medium_risk_keywords):
        return -0.2  # 中等风险
    elif any(keyword in text_lower for keyword in safe_keywords):
        return -0.8  # 低风险
    else:
        return -0.4  # 中性风险


def _infer_risk_level_from_score_and_tags(kp: dict) -> float:
    """Phase 2 Emergency Fix: Infer risk_level from score and tags"""
    score = kp.get("score", 0)
    tags = kp.get("tags", [])

    # 先基于评分推断基础风险
    base_risk = _infer_risk_level_from_text(kp.get("text", ""))

    # 根据历史评分调整
    if score >= 2:
        # 历史验证，降低风险认知
        return base_risk - 0.3
    elif score >= 1:
        return base_risk
    else:
        # 负分或零分，增加风险认知
        return base_risk + 0.2


def _infer_innovation_from_text(text: str) -> float:
    """Phase 2 Emergency Fix: Infer innovation_level from text content"""
    text_lower = text.lower()

    # 高创新关键词
    high_innovation_keywords = ["breakthrough", "revolutionary", "novel", "first-time", "pioneering", "quantum", "ai-driven", "machine-learning"]
    medium_innovation_keywords = ["clever", "smart", "intelligent", "advanced", "optimized", "improved", "creative"]
    standard_keywords = ["standard", "basic", "simple", "regular", "common", "traditional", "conventional"]

    if any(keyword in text_lower for keyword in high_innovation_keywords):
        return 0.9  # 高创新
    elif any(keyword in text_lower for keyword in medium_innovation_keywords):
        return 0.6  # 中等创新
    elif any(keyword in text_lower for keyword in standard_keywords):
        return 0.2  # 标准实践
    else:
        return 0.5  # 中等创新


def _infer_innovation_from_tags(tags: list[str]) -> float:
    """Phase 2 Emergency Fix: Infer innovation_level from tags"""
    if not tags:
        return 0.5

    # 创新技术标签
    innovation_tags = ["ai", "ml", "quantum", "blockchain", "ar", "vr", "experimental", "research"]
    advanced_tags = ["advanced", "modern", "next-gen", "cutting-edge", "optimization"]
    basic_tags = ["basic", "standard", "simple", "common"]

    tag_text = " ".join(tags).lower()

    if any(tag in tag_text for tag in innovation_tags):
        return 0.8  # 高创新
    elif any(tag in tag_text for tag in advanced_tags):
        return 0.6  # 中等创新
    elif any(tag in tag_text for tag in basic_tags):
        return 0.3  # 低创新
    else:
        return 0.5  # 中等创新
