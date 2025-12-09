#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import math
import threading

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# For semantic similarity calculation
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


def get_project_dir() -> Path:
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    return Path.home()


def get_user_claude_dir() -> Path:
    home = Path.home()
    return home / ".claude"


def is_diagnostic_mode() -> bool:
    flag_file = get_project_dir() / ".claude" / "diagnostic_mode"
    return flag_file.exists()


def save_diagnostic(content: str, name: str):
    diagnostic_dir = get_project_dir() / ".claude" / "diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = diagnostic_dir / f"{timestamp}_{name}.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


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


def normalize_tags(tags: Optional[list[str]], max_tags: int = 6) -> list[str]:
    """Normalize tag list to lowercase unique values with a soft cap."""
    normalized = []
    seen = set()

    tag_list = [tags] if isinstance(tags, str) else (tags or [])

    for tag in tag_list:
        if not isinstance(tag, str):
            continue
        clean = tag.strip().lower()
        # enforce ascii-only tags to keep output in English
        try:
            clean.encode("ascii")
        except UnicodeEncodeError:
            continue
        if not clean or clean in seen:
            continue
        normalized.append(clean[:64])
        seen.add(clean)
        if len(normalized) >= max_tags:
            break

    return normalized


# Global variables for sentence transformer model (lazy loading)
_sentence_model = None
_model_lock = threading.Lock()


def get_sentence_model():
    """Thread-safe lazy loading of sentence transformer model."""
    global _sentence_model
    if _sentence_model is None:
        with _model_lock:
            if _sentence_model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    # Use a lightweight multilingual model
                    _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                except Exception as e:
                    # Fallback if model loading fails
                    print(f"Warning: Failed to load sentence transformer model: {e}", file=sys.stderr)
                    _sentence_model = False
    return _sentence_model


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts using sentence transformers.
    Returns cosine similarity score between 0 and 1."""
    model = get_sentence_model()
    if not model:
        # Fallback to lexical similarity if semantic model unavailable
        return calculate_lexical_similarity(text1, text2)

    try:
        # Encode texts to vectors
        embeddings = model.encode([text1, text2])
        # Calculate cosine similarity
        cos_sim = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(cos_sim)
    except Exception:
        # Fallback to lexical similarity on error
        return calculate_lexical_similarity(text1, text2)


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
    """Find tags that are semantically similar to the target tag.
    Returns list of (tag, similarity_score) tuples above threshold."""
    similar_tags = []

    for tag in existing_tags:
        if tag.lower() == target_tag.lower():
            # Exact match gets highest score
            similar_tags.append((tag, 1.0))
            continue

        # Calculate semantic similarity
        similarity = calculate_semantic_similarity(target_tag, tag)
        if similarity >= threshold:
            similar_tags.append((tag, similarity))

    # Sort by similarity score (descending)
    similar_tags.sort(key=lambda x: x[1], reverse=True)
    return similar_tags


def get_tag_statistics_path() -> Path:
    return get_project_dir() / ".claude" / "tag_statistics.json"


def load_tag_statistics() -> dict:
    """Load tag statistics from separate JSON file."""
    stats_path = get_tag_statistics_path()

    if not stats_path.exists():
        return {
            "version": "1.0",
            "last_updated": None,
            "total_tags": 0,
            "total_usage": 0,
            "tags": {}
        }

    try:
        with open(stats_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": "1.0",
            "last_updated": None,
            "total_tags": 0,
            "total_usage": 0,
            "tags": {}
        }


def save_tag_statistics(stats: dict):
    """Save tag statistics to separate JSON file."""
    stats_path = get_tag_statistics_path()
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    stats["last_updated"] = datetime.now().isoformat()

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def update_tag_statistics(stats: dict, new_tags: List[str]) -> dict:
    """Update tag statistics with new tags and their usage statistics."""
    if "tags" not in stats:
        stats["tags"] = {}
    if "total_usage" not in stats:
        stats["total_usage"] = 0
    if "total_tags" not in stats:
        stats["total_tags"] = 0
    if "last_updated" not in stats:
        stats["last_updated"] = None

    tags_dict = stats["tags"]

    for tag in new_tags:
        tag_key = tag.lower()
        if tag_key not in tags_dict:
            tags_dict[tag_key] = {
                "canonical": tag,
                "usage_count": 0,
                "first_used": datetime.now().isoformat(),
                "last_used": None
            }
            stats["total_tags"] += 1

        # Update usage statistics
        tags_dict[tag_key]["usage_count"] += 1
        tags_dict[tag_key]["last_used"] = datetime.now().isoformat()
        stats["total_usage"] += 1

    stats["last_updated"] = datetime.now().isoformat()

    return stats


MAX_KEYPOINTS = 250  # hard cap to keep playbook manageable


def infer_tags_from_text(text: str, max_tags: int = 5) -> list[str]:
    """Heuristic tag extraction when no explicit tags are provided."""
    stopwords = {
        "the",
        "this",
        "that",
        "with",
        "from",
        "into",
        "your",
        "their",
        "have",
        "having",
        "using",
        "use",
        "used",
        "for",
        "and",
        "when",
        "while",
        "after",
        "before",
        "code",
        "error",
        "issue",
        "fix",
        "task",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())
    tags = []
    for word in words:
        if word in stopwords or word.isdigit():
            continue
        if word not in tags:
            tags.append(word)
        if len(tags) >= max_tags:
            break
    return tags


def generate_keypoint_name(existing_names: set) -> str:
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


def save_playbook(playbook: dict):
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
    except Exception as e:
        # Clean up temp file if something goes wrong
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        raise e


def format_playbook(
    playbook: dict,
    key_points: Optional[list[dict]] = None,
    tags: Optional[list[str]] = None,
) -> str:
    selected_key_points = key_points if key_points is not None else playbook.get("key_points", [])
    if not selected_key_points:
        return ""

    tags_text = ", ".join(tags) if tags else "all topics"
    key_points_text = "\n".join(
        f"- [score={kp.get('score', 0)}][tags={','.join(kp.get('tags', []))}] {kp.get('text', '')}"
        for kp in selected_key_points
        if isinstance(kp, dict)
    )

    template = load_template("playbook.txt")
    return template.format(key_points=key_points_text, tags=tags_text)


def update_playbook_data(playbook: dict, extraction_result: dict) -> dict:
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
        # If the model proposes fewer merged KPTs than existing ones, treat them as additions
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

        # Rebuild indices after any additions so downstream merge logic has the mappings.
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
    if len(playbook["key_points"]) > MAX_KEYPOINTS:
        playbook["key_points"] = sorted(
            playbook["key_points"],
            key=lambda kp: (-kp.get("score", 0), kp.get("name", "")),
        )[:MAX_KEYPOINTS]

    # Renumber key points sequentially to keep identifiers compact.
    for idx, kp in enumerate(playbook["key_points"], start=1):
        kp["name"] = f"kpt_{idx:03d}"

    return playbook


def select_relevant_keypoints(
    playbook: dict, tags: list[str], limit: int = 6, prompt_tags: Optional[list[str]] = None
) -> list[dict]:
    """Pick the highest scoring key points that match the requested tags."""
    key_points = playbook.get("key_points", [])
    if not key_points:
        return []

    desired_tags = [t.lower() for t in tags or [] if isinstance(t, str)]
    prompt_tag_set = {t.lower() for t in (prompt_tags or [])}

    def tag_match_score(kp_tag: str, desired: str) -> int:
        """Exact = 3, substring = 2, token overlap = 1, else 0."""
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


def load_transcript(transcript_path: str) -> list[dict]:
    conversations = []

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            entry = json.loads(line)

            if entry.get("type") not in ["user", "assistant"]:
                continue
            if entry.get("isMeta") or entry.get("isVisibleInTranscriptOnly"):
                continue

            message = entry.get("message", {})
            role = message.get("role")
            content = message.get("content", "")

            if not role or not content:
                continue

            if isinstance(content, str) and (
                "<command-name>" in content or "<local-command-stdout>" in content
            ):
                continue

            if isinstance(content, list):
                text_parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                if text_parts:
                    conversations.append(
                        {"role": role, "content": "\n".join(text_parts)}
                    )
            else:
                conversations.append({"role": role, "content": content})

    return conversations


def load_template(template_name: str) -> str:
    template_path = get_user_claude_dir() / "prompts" / template_name
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


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
    messages: list[dict], playbook: dict, diagnostic_name: str = "reflection"
) -> dict:
    client, model = get_anthropic_client()
    if not client:
        if is_diagnostic_mode():
            save_diagnostic("no client available for reflection", diagnostic_name)
        return {"new_key_points": [], "evaluations": []}

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
