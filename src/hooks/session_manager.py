"""Session management utilities."""

import json
import os
from pathlib import Path


def is_first_message(session_id: str) -> bool:
    """Check if this is the first message in the session."""
    user_claude_dir = Path(os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")))
    session_marker = user_claude_dir / f".{session_id}_first_message"
    return not session_marker.exists()


def mark_session(session_id: str):
    """Mark the session as having received its first message."""
    user_claude_dir = Path(os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")))
    session_marker = user_claude_dir / f".{session_id}_first_message"
    session_marker.touch()


def clear_session():
    """Clear session markers."""
    user_claude_dir = Path(os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")))
    for marker in user_claude_dir.glob("._first_message"):
        marker.unlink()