"""Base class for extraction hooks."""

import json
import sys
import asyncio
from typing import Optional

from utils import load_transcript, load_settings
from playbook_manager import (
    load_playbook,
    save_playbook,
    update_playbook_data,
)
from llm_client import extract_keypoints
from session_manager import clear_session


class ExtractionHook:
    """Base class for hooks that extract keypoints from transcripts."""

    def __init__(self, diagnostic_name: str):
        self.diagnostic_name = diagnostic_name
        self.needs_settings = False
        self.allowed_reasons = None

    async def run(self):
        """Run the extraction hook."""
        input_data = json.load(sys.stdin)

        transcript_path = input_data.get("transcript_path")
        messages = load_transcript(transcript_path)

        if not messages:
            sys.exit(0)

        # Check settings if needed
        if self.needs_settings and self.allowed_reasons:
            settings = load_settings()
            reason = input_data.get("reason", "")

            for setting_key, allowed_reason in self.allowed_reasons.items():
                update_setting = settings.get(setting_key, False)
                if not update_setting and reason == allowed_reason:
                    sys.exit(0)

        # Extract and update playbook
        playbook = load_playbook()
        extraction_result = await extract_keypoints(
            messages, playbook, self.diagnostic_name
        )
        playbook = update_playbook_data(playbook, extraction_result)
        save_playbook(playbook)

        clear_session()

    def main(self):
        """Entry point for the script."""
        try:
            asyncio.run(self.run())
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)