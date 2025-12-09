[Root Directory](../../../../CLAUDE.md) > [src](../../../) > [hooks](../../) > [utils](../) > **utils**

# Utils Module

## Module Responsibilities

The utils module provides shared utilities and helper functions for the Agentic Context Engineering system. It contains specialized utilities for path management, tag operations, and common functionality used across all hook implementations.

## Entry and Startup

### Module Structure
- `path_utils.py` - Path and directory management utilities
- `tag_utils.py` - Tag normalization, inference, and management
- `__init__.py` - Module initialization and exports

### Import Pattern
```python
from .utils.path_utils import get_project_dir, get_user_claude_dir
from .utils.tag_utils import normalize_tags, infer_tags_from_text
```

## External Interfaces

### Path Utilities (`path_utils.py`)
- `get_project_dir()` - Get project directory from environment
- `get_user_claude_dir()` - Get user's Claude configuration directory
- `is_diagnostic_mode()` - Check if diagnostic mode is enabled
- `save_diagnostic()` - Save diagnostic content with timestamp

### Tag Utilities (`tag_utils.py`)
- `normalize_tags()` - Clean and standardize tag formats
- `infer_tags_from_text()` - Extract relevant tags from text content
- Tag similarity and matching functions

## Key Dependencies and Configuration

### Internal Dependencies
- No internal module dependencies
- Pure utility functions with minimal coupling

### External Dependencies
- Python standard library only:
  - `pathlib` - Path operations
  - `os` - Environment variables
  - `re` - Regular expressions
  - `datetime` - Timestamp generation

### Configuration
- `CLAUDE_PROJECT_DIR` environment variable
- `.claude/diagnostic_mode` flag file
- Diagnostic output directory: `.claude/diagnostic/`

## Data Models

### Diagnostic Entry
```python
{
    "timestamp": "YYYYMMDD_HHMMSS",
    "name": "diagnostic_category",
    "content": "Diagnostic information"
}
```

### Tag Structure
- Tags are lowercase ASCII strings
- Maximum length: 64 characters
- Hyphens allowed for multi-word tags
- Automatic deduplication and normalization

## Testing and Quality

### Unit Tests
- Test path resolution with various environment configurations
- Validate tag normalization and inference accuracy
- Test diagnostic file creation and rotation

### Quality Assurance
- Type hints for all function signatures
- Comprehensive docstrings with examples
- Graceful error handling with fallbacks

## Frequently Asked Questions (FAQ)

**Q: Where are diagnostic files saved?**
A: In `.claude/diagnostic/` with timestamp prefix: `YYYYMMDD_HHMMSS_category.txt`

**Q: How are tags normalized?**
A: Converted to lowercase, ASCII only, max 64 chars, hyphens preserved

**Q: What's the difference between project dir and user dir?**
A: Project dir is current working directory, user dir is `~/.claude/`

## Related File List

### Core Files
- `path_utils.py` - Directory and path management
- `tag_utils.py` - Tag processing and normalization
- `__init__.py` - Module initialization

### Usage Examples
Used by:
- `../common.py` - Shared functionality
- `../playbook_engine.py` - Knowledge operations
- `../user_prompt_inject.py` - Knowledge injection
- `../session_end.py` - Knowledge extraction

## Change Log (Changelog)

### 2025-12-09 22:14:39
- Initial module documentation
- Added navigation breadcrumbs
- Documented utility interfaces and data models

---
*Last updated: 2025-12-09 22:14:39*