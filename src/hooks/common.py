#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


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


def load_playbook() -> dict:
    playbook_path = get_project_dir() / ".claude" / "playbook.json"

    if not playbook_path.exists():
        return {"version": "1.0", "last_updated": None, "key_points": []}

    def _is_divider(entry: object) -> bool:
        return isinstance(entry, dict) and entry.get("divider") is True

    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = json.load(f)

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

    except Exception:
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

    with open(playbook_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


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

    rating_delta = {"helpful": 1, "harmful": -3, "neutral": -1}
    name_to_kp = {kp["name"]: kp for kp in playbook["key_points"]}

    # Apply evaluations first so scores are updated before merges.
    for eval_item in evaluations:
        name = eval_item.get("name", "")
        rating = eval_item.get("rating", "neutral")
        if name in name_to_kp:
            name_to_kp[name]["score"] += rating_delta.get(rating, 0)

    if merged_key_points is not None:
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
    messages: list[dict], prompt_text: str = "", diagnostic_name: str = "tagger"
) -> tuple[list[str], list[str]]:
    """Generate request tags from recent conversation history and the pending prompt."""
    prompt_seed_tags = normalize_tags(infer_tags_from_text(prompt_text, max_tags=4))

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
    )

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

    combined = normalize_tags(prompt_seed_tags + llm_tags, max_tags=6)
    combined = combined or prompt_seed_tags
    return combined, prompt_seed_tags


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

    prompt = template.format(
        trajectories=json.dumps(messages, indent=2, ensure_ascii=False),
        existing_playbook=json.dumps(
            existing_playbook, indent=2, ensure_ascii=False
        ),
        pending_playbook=json.dumps(
            pending_playbook, indent=2, ensure_ascii=False
        ),
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
