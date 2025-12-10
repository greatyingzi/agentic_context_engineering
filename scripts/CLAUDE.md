[Root Directory](../../CLAUDE.md) > **scripts**

# Scripts Module

## Module Responsibilities

The scripts module contains helper scripts for managing and bootstrapping the Agentic Context Engineering system. These scripts provide utilities for initializing knowledge bases from historical data and performing maintenance operations.

## Entry and Startup

### Script Entry Points
- `bootstrap_playbook.py` - Initialize playbook from historical Claude transcripts

### Execution Pattern
```bash
# Direct execution
python bootstrap_playbook.py [options]

# Via Claude Code command
/init-playbook --limit 100 --order newest
```

## External Interfaces

### Bootstrap Script Interface
- `--history-dir` - Custom history directory path
- `--project-dir` - Target project directory
- `--limit` - Maximum transcripts to process (default: 50)
- `--order` - Processing order: oldest/newest (default: oldest)
- `--force` - Rebuild from empty playbook
- `--diagnostic-name` - Diagnostic log identifier

### Claude Code Integration
Script is exposed as `/init-playbook` command via `../src/commands/init-playbook.md`

## Key Dependencies and Configuration

### Internal Dependencies
- `../src/hooks/common.py` - Core hook functionality
- `../src/hooks/utils/` - Utility functions
- Anthropic Claude API for intelligent analysis

### External Dependencies
- `anthropic` - LLM client
- Python standard library:
  - `asyncio` - Asynchronous processing
  - `pathlib` - Path operations
  - `argparse` - Command line parsing

### Configuration
- `AGENTIC_CONTEXT_API_KEY` - API key for Claude
- `AGENTIC_CONTEXT_MODEL` - Model selection
- `AGENTIC_CONTEXT_BASE_URL` - Custom API endpoint
- Environment file: `~/.claude/env`

## Data Models

### Transcript Format
```json
{"type": "user|assistant", "message": {"role": "user|assistant", "content": "..."}}
```

### Processing Output
```
[start] history_dir=..., files=N, limit=N, force=false, order=newest
[processing] transcript_20240101_120000.jsonl …
[ok] transcript_20240101_120000.jsonl: +3 (total=3)
[success] bootstrap complete: processed=N, total_kpts=N
```

## Testing and Quality

### Test Coverage
- Mock historical data for consistent testing
- Validate playbook structure after bootstrap
- Test various command line options

### Quality Features
- Progress tracking and reporting
- Diagnostic logging for troubleshooting
- Atomic playbook updates to prevent corruption
- Graceful handling of malformed transcripts

## Frequently Asked Questions (FAQ)

**Q: Where does the script find historical transcripts?**
A: Automatically discovers in `~/.claude/projects/` or uses `--history-dir`

**Q: Can I reprocess already processed transcripts?**
A: Yes, use `--force` flag to rebuild from empty playbook

**Q: How do I limit processing to recent conversations?**
A: Use `--limit N` and `--order newest` options

## Related File List

### Core Script
- `bootstrap_playbook.py` - Main bootstrap implementation

### Integration Points
- `../src/commands/init-playbook.md` - Claude Code command definition
- `../src/hooks/common.py` - Imported functionality
- `../src/hooks/utils/` - Utility modules

### Output Files
- `.claude/playbook.json` - Generated knowledge base
- `.claude/diagnostic/` - Diagnostic logs when enabled

## Change Log (Changelog)

### 2025-12-09 22:14:39
- Initial module documentation
- Added navigation breadcrumbs
- Documented script interface and options

---
*Last updated: 2025-12-09 22:14:39*