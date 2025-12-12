#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

from common import (
    clear_session,
    extract_keypoints,
    get_exception_handler,
    is_diagnostic_mode,
    load_playbook,
    load_settings,
    load_transcript,
    save_diagnostic,
    save_playbook,
    update_playbook_data,
    load_session_injections,
    clear_session_injections,
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
            if is_diagnostic_mode():
                save_diagnostic(
                    f"No messages found in transcript: {transcript_path}. "
                    f"Transcript exists: {Path(transcript_path).exists() if transcript_path else 'No path provided'}",
                    "session_end_no_messages",
                )
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

        # Load session-injected KPTs for targeted reflection
        session_injected_kpts = load_session_injections(session_id)

        if is_diagnostic_mode():
            save_diagnostic(
                f"Starting key points extraction. Current playbook has {len(playbook.get('key_points', []))} key points, "
                f"session injected KPTs: {len(session_injected_kpts)} items",
                "session_end_extraction_start",
            )

        extraction_result = await extract_keypoints(
            messages, playbook, "session_end_reflection", session_injected_kpts
        )

        new_points_count = len(extraction_result.get("new_key_points", []))
        if is_diagnostic_mode():
            save_diagnostic(
                f"Extracted {new_points_count} new key points",
                "session_end_extraction_result",
            )

        playbook = update_playbook_data(playbook, extraction_result)

        final_count = len(playbook.get("key_points", []))
        if is_diagnostic_mode():
            save_diagnostic(
                f"Saving playbook with {final_count} total key points",
                "session_end_save",
            )

        save_success = save_playbook(playbook)

        # Clear session injection records after processing
        clear_session_injections(session_id)

        if is_diagnostic_mode():
            if save_success:
                save_diagnostic(
                    "Playbook saved successfully", "session_end_save_success"
                )
            else:
                save_diagnostic(
                    "Playbook save failed - no error details available",
                    "session_end_save_failed",
                )

        clear_session()

    except Exception as e:
        # Use global exception handler for consistent error logging and user feedback
        context_data = {
            "input_data": input_data
            if "input_data" in locals()
            else "Unable to capture",
            "reason": input_data.get("reason")
            if "input_data" in locals()
            else "unknown",
            "hook_stage": "main_execution",
        }
        handler.handle_and_exit(
            e,
            "session_end",
            context_data,
            session_id if "session_id" in locals() else None,
        )


if __name__ == "__main__":
    asyncio.run(main())
