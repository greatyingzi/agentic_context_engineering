#!/usr/bin/env python3
from extraction_hook_base import ExtractionHook


class SessionEndHook(ExtractionHook):
    """Hook for extracting keypoints at session end."""

    def __init__(self):
        super().__init__("session_end_reflection")
        self.needs_settings = True
        self.allowed_reasons = {
            "playbook_update_on_exit": "prompt_input_exit",
            "playbook_update_on_clear": "clear",
        }


if __name__ == "__main__":
    hook = SessionEndHook()
    hook.main()