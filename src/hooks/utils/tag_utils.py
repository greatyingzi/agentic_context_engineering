"""Tag-related utilities for context engine."""

import re
from typing import List, Optional


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