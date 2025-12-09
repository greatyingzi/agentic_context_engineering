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
    get_exception_handler,
)


async def main():
    handler = get_exception_handler()

    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path")

        messages = load_transcript(transcript_path)

        if not messages:
            sys.exit(0)

        playbook = load_playbook()
        extraction_result = await extract_keypoints(
            messages, playbook, "precompact_reflection"
        )
        playbook = update_playbook_data(playbook, extraction_result)
        save_playbook(playbook)

        clear_session()

    except Exception as e:
        # Use global exception handler for consistent error logging and user feedback
        context_data = {
            "input_data": input_data if 'input_data' in locals() else "Unable to capture",
            "hook_stage": "main_execution"
        }
        handler.handle_and_exit(e, "precompact", context_data, session_id if 'session_id' in locals() else None)


if __name__ == "__main__":
    asyncio.run(main())
