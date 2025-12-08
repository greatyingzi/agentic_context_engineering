"""Common interface for all modules.

This module provides backward compatibility by importing from the new modular structure.
"""

# Import all functions from their respective modules
from utils import *
from session_manager import *
from tag_manager import *
from llm_client import *
from playbook_manager import *

# Re-export everything for backward compatibility
__all__ = [
    # From utils
    "get_project_dir",
    "get_user_claude_dir",
    "is_diagnostic_mode",
    "save_diagnostic",
    "load_transcript",
    "load_template",
    "load_settings",
    # From session_manager
    "is_first_message",
    "mark_session",
    "clear_session",
    # From tag_manager
    "normalize_tags",
    "get_tag_statistics_path",
    "load_tag_statistics",
    "save_tag_statistics",
    "update_tag_statistics",
    # From llm_client
    "get_anthropic_client",
    "generate_tags_from_messages",
    "infer_tags_from_text",
    "generate_keypoint_name",
    "extract_keypoints",
    # From playbook_manager
    "validate_playbook_structure",
    "load_playbook",
    "save_playbook",
    "format_playbook",
    "update_playbook_data",
    "select_relevant_keypoints",
]