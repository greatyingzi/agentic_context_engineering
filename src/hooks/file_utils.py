#!/usr/bin/env python3
"""File utilities for loading transcripts and templates."""
import json
from pathlib import Path

# Import path utilities
try:
    from .utils.path_utils import get_user_claude_dir
except ImportError:
    # Fallback for direct execution or testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.path_utils import get_user_claude_dir


def load_transcript(transcript_path: str) -> list[dict]:
    """Load and parse transcript from file.

    Args:
        transcript_path: Path to the transcript file

    Returns:
        List of conversation messages with role and content
        Returns empty list if file doesn't exist or can't be read
    """
    conversations = []

    # Check if transcript file exists
    transcript_file = Path(transcript_path)
    if not transcript_file.exists():
        return conversations

    try:
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

    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
        # Log the error but don't crash - return empty conversations
        # This allows hooks to continue gracefully even with corrupted transcript files
        pass

    return conversations


def load_template(template_name: str) -> str:
    """Load template from file.

    Args:
        template_name: Name of the template file

    Returns:
        Template content as string
    """
    template_path = get_user_claude_dir() / "prompts" / template_name
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()