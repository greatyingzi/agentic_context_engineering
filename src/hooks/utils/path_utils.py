#!/usr/bin/env python3
"""
Path and directory utilities for Claude hooks.
"""
import os
from datetime import datetime
from pathlib import Path


def get_project_dir() -> Path:
    """Get the project directory from environment or fallback to home."""
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    return Path.home()


def get_user_claude_dir() -> Path:
    """Get the user's Claude configuration directory."""
    home = Path.home()
    return home / ".claude"


def is_diagnostic_mode() -> bool:
    """Check if diagnostic mode is enabled."""
    flag_file = get_project_dir() / ".claude" / "diagnostic_mode"
    return flag_file.exists()


def save_diagnostic(content: str, name: str):
    """Save diagnostic content to a timestamped file."""
    diagnostic_dir = get_project_dir() / ".claude" / "diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = diagnostic_dir / f"{timestamp}_{name}.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)