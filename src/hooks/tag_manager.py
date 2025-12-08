"""Tag management utilities."""

import json
import os
from pathlib import Path
from typing import List, Optional
import re


def normalize_tags(tags: Optional[list[str]], max_tags: int = 6) -> list[str]:
    """Normalize and clean a list of tags."""
    if not tags:
        return []

    normalized = []
    seen = set()

    for tag in tags:
        if isinstance(tag, str):
            # Convert to lowercase and strip whitespace
            cleaned = tag.lower().strip()

            # Remove special characters and normalize spaces
            cleaned = re.sub(r'[^\w\s_-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            # Skip empty strings or duplicates
            if cleaned and cleaned not in seen and len(cleaned) <= 50:
                seen.add(cleaned)
                normalized.append(cleaned)

                if len(normalized) >= max_tags:
                    break

    return normalized


def get_tag_statistics_path() -> Path:
    """Get path to tag statistics JSON file in project's diagnostic directory."""
    project_dir = Path.cwd()
    return project_dir / ".claude" / "diagnostic" / "tag_statistics.json"


def load_tag_statistics() -> dict:
    """Load tag usage statistics."""
    stats_path = get_tag_statistics_path()
    if stats_path.exists():
        try:
            with open(stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_tag_statistics(stats: dict):
    """Save tag usage statistics."""
    stats_path = get_tag_statistics_path()
    stats_path.parent.mkdir(exist_ok=True, parents=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def update_tag_statistics(stats: dict, new_tags: List[str]) -> dict:
    """Update tag statistics with new tags."""
    for tag in new_tags:
        stats[tag] = stats.get(tag, 0) + 1
    return stats