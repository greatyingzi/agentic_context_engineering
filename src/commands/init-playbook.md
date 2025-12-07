---
name: init-playbook
description: Bootstrap playbook.json from historical Claude transcripts
allowed-tools:
  - Exec($HOME/.claude/.venv/bin/python3)
argument-hint: ""
---

# init-playbook

Bootstrap the current repo playbook from historical Claude transcripts.

---

## Command (executed by this slash command)
```bash
"$HOME/.claude/.venv/bin/python3" "$HOME/.claude/scripts/bootstrap_playbook.py"
```