#!/usr/bin/env python3
import json
import sys
from common import (
    load_playbook,
    format_playbook,
    is_diagnostic_mode,
    save_diagnostic,
    load_transcript,
    generate_task_guidance,
    select_relevant_keypoints,
    load_template,
)


def format_guidance_for_user(guidance_result: dict) -> str:
    """Format the LLM-generated task guidance into user-friendly context"""

    brief_guidance = guidance_result.get("brief_guidance", "")

    # If no guidance text, return empty string
    if not brief_guidance.strip():
        return ""

    # Simple format showing only core reminder
    return f"### 💡 Task Guidance\n{brief_guidance}"


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

    # 使用新的任务引导函数
    result = generate_task_guidance(
        messages, prompt_text, playbook=playbook, diagnostic_name="task_guidance"
    )

    tags_data = result.get("tags", {})
    tags = tags_data.get("final_tags", [])
    prompt_tags = tags_data.get("seed_tags", [])

    guidance_result = result.get("task_guidance", {})

    # 格式化引导结果用于用户显示
    guidance_text = format_guidance_for_user(guidance_result)

    selected_key_points = select_relevant_keypoints(
        playbook, tags, limit=6, prompt_tags=prompt_tags
    )
    context = format_playbook(playbook, key_points=selected_key_points, tags=tags)

    if not context.strip():
        print(json.dumps({}), flush=True)
        sys.exit(0)

    # 如果有引导结果，将其添加到上下文前面
    if guidance_text:
        context = guidance_text + "\n\n" + context

    if is_diagnostic_mode():
        diagnostic_payload = {
            "session_id": session_id,
            "prompt": prompt_text,
            "tags": tags,  # Final generated/selected tags
            "selected": [kp.get("name") for kp in selected_key_points],
            "context": context,  # Final context to be injected
            "task_guidance": guidance_result
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