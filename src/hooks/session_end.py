#!/usr/bin/env python3
import json
import sys
import asyncio
from common import (
    load_playbook,
    save_playbook,
    load_transcript,
    extract_keypoints,
    update_playbook_data,
    clear_session,
    load_settings,
    get_exception_handler,
)


async def main():
    handler = get_exception_handler()

    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path")
        reason = input_data.get("reason", "")

        messages = load_transcript(transcript_path)

        if not messages:
            sys.exit(0)

        settings = load_settings()
        update_on_exit = settings.get("playbook_update_on_exit", False)
        update_on_clear = settings.get("playbook_update_on_clear", False)

        # Skip playbook update for /exit command when setting is disabled
        if not update_on_exit and reason == "prompt_input_exit":
            sys.exit(0)

        # Skip playbook update for /clear command when setting is disabled
        if not update_on_clear and reason == "clear":
            sys.exit(0)

        playbook = load_playbook()
        extraction_result = await extract_keypoints(
            messages, playbook, "session_end_reflection"
        )
        playbook = update_playbook_data(playbook, extraction_result)
        save_playbook(playbook)

        clear_session()

    except Exception as e:
        # Use global exception handler for consistent error logging and user feedback
        context_data = {
            "input_data": input_data if 'input_data' in locals() else "Unable to capture",
            "reason": input_data.get("reason") if 'input_data' in locals() else "unknown",
            "hook_stage": "main_execution"
        }
        handler.handle_and_exit(e, "session_end", context_data, session_id if 'session_id' in locals() else None)


if __name__ == "__main__":
    asyncio.run(main())
