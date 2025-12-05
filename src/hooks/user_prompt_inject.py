#!/usr/bin/env python3
import json
import sys
from common import (
    load_playbook,
    format_playbook,
    is_diagnostic_mode,
    save_diagnostic,
    load_transcript,
    generate_tags_from_messages,
    select_relevant_keypoints,
)


def main():
    input_data = json.load(sys.stdin)
    session_id = input_data.get("session_id", "unknown")
    prompt_text = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")

    playbook = load_playbook()

    messages = []
    if transcript_path:
        try:
            messages = load_transcript(transcript_path)
        except Exception:
            messages = []

    tags, prompt_tags = generate_tags_from_messages(messages, prompt_text)
    selected_key_points = select_relevant_keypoints(
        playbook, tags, limit=6, prompt_tags=prompt_tags
    )
    context = format_playbook(playbook, key_points=selected_key_points, tags=tags)

    if not context:
        print(json.dumps({}), flush=True)
        sys.exit(0)

    if is_diagnostic_mode():
        diagnostic_payload = {
            "session_id": session_id,
            "prompt": prompt_text,
            "tags": tags,
            "prompt_tags": prompt_tags,
            "selected": [kp.get("name") for kp in selected_key_points],
            "context": context,
        }
        save_diagnostic(json.dumps(diagnostic_payload, indent=2, ensure_ascii=False), "user_prompt_inject")

    response = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(response), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        print(json.dumps({}), flush=True)
        sys.exit(1)
