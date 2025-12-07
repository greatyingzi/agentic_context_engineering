# Agentic Context Engineering

A simplified implementation of Agentic Context Engineering (ACE) for Claude Code that automatically learns and accumulates key points from reasoning trajectories.

## Features

- **Automatic Key Point Extraction**: Learns from reasoning trajectories and extracts valuable insights
- **Score-Based Filtering & Merging**: Evaluates key points across trajectories, merges near-duplicate KPTs (LLM-driven, ≥80% semantic similarity) while summing their scores, and removes unhelpful ones
- **Tag-Aware Retrieval**: Assigns tags to key points and injects the highest-scoring, tag-matched items for each prompt
- **Context Injection**: Automatically injects accumulated knowledge at the start of new sessions
- **Multiple Triggers**: Works on session end, manual clear (`/clear`), and context compaction

## Installation

### Prerequisites

- Python 3.8+
- Claude Code
- [anthropic](https://github.com/anthropics/anthropic-sdk-python) Python SDK
- Node.js and npm

### Setup

1. Clone and install:
```bash
git clone https://github.com/bluenoah1991/agentic_context_engineering.git
cd agentic_context_engineering
npm install
```

2. Install required Python package (recommend uv):
```bash
# with uv
uv venv ~/.claude/.venv
uv pip install --python ~/.claude/.venv/bin/python3 anthropic

# or with pip
pip3 install anthropic
```

3. Set environment variables for the LLM API:

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `AGENTIC_CONTEXT_MODEL` | Model name for key point extraction (fallback: `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `claude-sonnet-4-5-20250929`) | Optional |
| `AGENTIC_CONTEXT_API_KEY` | API key (fallback: `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`) | Optional |
| `AGENTIC_CONTEXT_BASE_URL` | API base URL (fallback: `ANTHROPIC_BASE_URL`) | Optional |

4. Restart Claude Code - hooks will be active across all your projects

## How It Works

### Hooks

The system uses three types of hooks:

1. **UserPromptSubmit**: Injects accumulated key points at the start of each new session
2. **SessionEnd**: Extracts key points when a session ends
3. **PreCompact**: Extracts key points before context compaction

### Key Point Lifecycle

1. **Extraction**: At the end of each session, the system analyzes the reasoning trajectories and extracts new key points
2. **Evaluation**: Existing key points are evaluated based on the reasoning trajectories and rated as helpful/harmful/neutral
3. **Scoring**: 
   - Helpful: +1 point
   - Harmful: -3 points
   - Neutral: -1 point
4. **Merging**: During reflection, the LLM clusters existing + pending + new candidates; only items with semantic similarity ≥80% are merged. Merged KPT scores are summed (positive/negative), tags deduped, and pending items “graduate” to stable.
5. **Tagging**: Each key point is stored with concise tags for topical retrieval
6. **Pruning**: Key points with score ≤ -5 are automatically removed
7. **Renumbering**: After updates, KPT names are compacted sequentially (`kpt_001`, `kpt_002`, …).
8. **Injection**: For each prompt, conversation history is tagged and the highest-scoring matching key points are injected

### Playbook Layout

- Stable KPTs are listed first; pending KPTs (if any) are separated by a divider line in `.claude/playbook.json`. Stable items omit the `pending` field; pending items carry `"pending": true`.

### Prompts

- Runtime prompt files live under `~/.claude/prompts/` (not the repo copy):
  - `reflection.txt`: extraction/merge + evaluation template (≥80% similarity required to merge).
  - `playbook.txt`: injection template.

## Init Playbook Command

Use `/init-playbook` to replay historical transcripts and build `.claude/playbook.json` for the current project.

- Command file is installed to `~/.claude/commands/init-playbook.md`.
- Helper script `bootstrap_playbook.py` is installed to `~/.claude/scripts/` (override via `ACE_BOOTSTRAP_SCRIPT`).
- Secrets: put `AGENTIC_CONTEXT_API_KEY`, `AGENTIC_CONTEXT_BASE_URL`, `AGENTIC_CONTEXT_MODEL` (or `ANTHROPIC_*`) in `~/.claude/env` (KEY=VAL, one per line) or export in your shell; the Python script auto-loads and normalizes them.
- Defaults: `--order oldest`, `--limit 200`; history dir auto-derives from project path (`~/.claude/projects/-<project-path>`). Override with `ACE_HISTORY_DIR`, `ACE_INIT_LIMIT`, `ACE_INIT_ORDER`, `ACE_INIT_FORCE` (start fresh).
- One-liner to run (no extra env wiring needed if `~/.claude/env` is set):
  ```
  "$HOME/.claude/.venv/bin/python3" "${ACE_BOOTSTRAP_SCRIPT:-$HOME/.claude/scripts/bootstrap_playbook.py}" \
    --history-dir "${ACE_HISTORY_DIR:-$HOME/.claude/projects/$(echo "${CLAUDE_PROJECT_DIR:-$(pwd)}" | sed 's#/#-#g')}" \
    --project-dir "${CLAUDE_PROJECT_DIR:-$(pwd)}" \
    --limit "${ACE_INIT_LIMIT:-200}" \
    --order "${ACE_INIT_ORDER:-oldest}" \
    ${ACE_INIT_FORCE:+--force}
  ```
- Logs: `./.claude/diagnostic/command_trace.log` and `~/.claude/diagnostic/command_trace.log`.

## Configuration

### Diagnostic Mode

To enable detailed logging of LLM interactions:

```bash
touch .claude/diagnostic_mode
```

Diagnostic logs will be saved to `.claude/diagnostic/` with timestamped filenames.

To disable:
```bash
rm .claude/diagnostic_mode
```

### `/exit` Command Behavior

By default, the system does **not** update the playbook when using `/exit`. You can enable this behavior by setting `playbook_update_on_exit` to `true` in your `~/.claude/settings.json`:

```json
{
  "playbook_update_on_exit": true
}
```

### `/clear` Command Behavior

By default, the system does **not** update the playbook when using `/clear`. You can enable this behavior by setting `playbook_update_on_clear` to `true` in your `~/.claude/settings.json`:

```json
{
  "playbook_update_on_clear": true
}
```

### Customizing Prompts

Prompts are located in `~/.claude/prompts/`:

- `reflection.txt`: Template for key point extraction from reasoning trajectories
- `playbook.txt`: Template for injecting key points into sessions

## File Structure

```
.
├── install.js                 # Installation script
├── package.json               # npm package configuration
├── src/
│   ├── hooks/
│   │   ├── common.py           # Shared utilities
│   │   ├── session_end.py      # SessionEnd hook
│   │   ├── precompact.py       # PreCompact hook
│   │   └── user_prompt_inject.py  # UserPromptSubmit hook
│   ├── prompts/
│   │   ├── reflection.txt      # Key point extraction template
│   │   └── playbook.txt        # Injection template
│   └── settings.json           # Hook configuration template
└── README.md
```

## License

MIT
