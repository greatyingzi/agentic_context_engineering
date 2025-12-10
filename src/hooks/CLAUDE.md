[Root Directory](../../../CLAUDE.md) > [src](../../) > [hooks](../) > **hooks**

# Hooks Module

## Module Responsibilities

The hooks module is the core integration point between Agentic Context Engineering and Claude Code. It implements three main hooks that automate knowledge extraction, evaluation, and injection throughout the conversation lifecycle.

## Entry and Startup

### Hook Entry Points
- `user_prompt_inject.py` - Injects relevant knowledge at session start
- `session_end.py` - Extracts insights when session ends
- `precompact.py` - Protects knowledge before context compaction

### Hook Registration
Hooks are registered in `~/.claude/settings.json` via the installation script with:
- UserPromptSubmit hook (10s timeout)
- SessionEnd hook (120s timeout)
- PreCompact hook (120s timeout)

## External Interfaces

### Claude Code Integration
- Hooks receive stdin with JSON event data
- Output to stdout for context injection
- Access to project directory via `CLAUDE_PROJECT_DIR`
- Session tracking via `.claude/last_session.txt`

### API Interfaces
- Anthropic Claude API for intelligent analysis
- Configuration via environment variables:
  - `AGENTIC_CONTEXT_API_KEY`
  - `AGENTIC_CONTEXT_MODEL`
  - `AGENTIC_CONTEXT_BASE_URL`

## Key Dependencies and Configuration

### Internal Dependencies
- `utils/` - Path management, tagging utilities
- `file_utils.py` - File loading operations
- `playbook_engine.py` - Knowledge base operations

### External Dependencies
- `anthropic` - LLM client for intelligent analysis
- Python standard library (pathlib, json, os, sys)

### Configuration Files
- `.claude/settings.json` - Hook configuration
- `.claude/playbook.json` - Knowledge storage
- `.claude/last_session.txt` - Session tracking

## Data Models

### Playbook Structure
```json
{
  "version": "1.0",
  "last_updated": "ISO-8601 timestamp",
  "key_points": [
    {
      "name": "kpt_XXX",
      "text": "Knowledge point text",
      "score": 0,
      "tags": ["tag1", "tag2"],
      "pending": false
    }
  ]
}
```

### Message Structure
```json
{
  "type": "user|assistant",
  "message": {
    "role": "user|assistant",
    "content": "Message content"
  }
}
```

## Testing and Quality

### Unit Tests
- Test utility functions in `utils/` subdirectory
- Mock Claude API responses for consistent testing
- Validate playbook structure and operations

### Integration Tests
- End-to-end hook execution workflows
- Session state management
- Knowledge extraction and injection cycles

### Quality Tools
- Diagnostic mode via `.claude/diagnostic_mode`
- Detailed logging to `.claude/diagnostic/`
- Atomic file operations for data integrity

## Frequently Asked Questions (FAQ)

**Q: How do I debug hook execution?**
A: Create `.claude/diagnostic_mode` file to enable detailed logging.

**Q: Why is knowledge not being injected?**
A: Check if API key is configured and hook timeouts are appropriate.

**Q: How can I manually trigger knowledge extraction?**
A: Use the `/init-playbook` command with appropriate options.

## Related File List

### Core Hook Files
- `user_prompt_inject.py` - Knowledge injection at session start
- `session_end.py` - Knowledge extraction at session end
- `precompact.py` - Knowledge protection before compaction
- `common.py` - Backward compatibility and shared functions

### Support Files
- `file_utils.py` - File operations utilities
- `utils/` - Utility submodules
  - `path_utils.py` - Path and directory utilities
  - `tag_utils.py` - Tag normalization and management

### External Dependencies
- `../prompts/` - LLM prompt templates
- `../settings.json` - Configuration template

## Change Log (Changelog)

### 2025-12-09 22:14:39
- Initial module documentation
- Added navigation breadcrumbs
- Documented hook interfaces and data models

---
*Last updated: 2025-12-09 22:14:39*