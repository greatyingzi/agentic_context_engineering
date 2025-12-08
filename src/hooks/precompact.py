#!/usr/bin/env python3
from extraction_hook_base import ExtractionHook


class PreCompactHook(ExtractionHook):
    """Hook for extracting keypoints during precompaction."""

    def __init__(self):
        super().__init__("precompact_reflection")
        # No settings checking needed for precompact
        self.needs_settings = False
        self.allowed_reasons = None


if __name__ == "__main__":
    hook = PreCompactHook()
    hook.main()