"""Common utility functions."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_project_dir() -> Path:
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return Path.cwd()
    return Path(project_dir)


def get_user_claude_dir() -> Path:
    config_dir = os.getenv("CLAUDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)

    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", "")) / ".claude"
    else:
        return Path(os.environ.get("HOME", "")) / ".claude"


def is_diagnostic_mode() -> bool:
    return os.getenv("ACE_DIAGNOSTIC", "false").lower() == "true"


def save_diagnostic(content: str, name: str):
    """Save diagnostic output to the project's .claude/diagnostic directory."""
    project_dir = Path.cwd()
    diagnostic_dir = project_dir / ".claude" / "diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = diagnostic_dir / f"{timestamp}_{name}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def load_transcript(transcript_path: Optional[str]) -> list[dict]:
    """Load transcript from file path. Returns empty list if path is None."""
    if not transcript_path:
        return []

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


def load_settings() -> dict:
    user_claude_dir = get_user_claude_dir()
    settings_path = user_claude_dir / "settings.json"
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}