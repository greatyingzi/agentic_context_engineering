---
name: spec-drive
description: Show openspec status (auto-injected) and refresh cache
allowed-tools:
  - Exec($HOME/.claude/.venv/bin/python3)
argument-hint: ""
---

# spec-drive

Spec is auto-injected on every prompt. Use this command only for diagnostics:

---

## Command (diagnostic)
```bash
"$HOME/.claude/.venv/bin/python3" - <<'PY'
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src" / "hooks"))
try:
    from openspec_loader import load_or_generate, _build_config  # type: ignore
    from playbook_engine import load_settings  # type: ignore
except Exception as e:
    print("failed to load modules:", e)
    sys.exit(1)

settings = load_settings()
config = _build_config(settings)
loaded = load_or_generate(config.spec_paths, config)
profiles = loaded.get("profiles", {})
print(json.dumps({"profiles": list(profiles.keys()), "paths": config.spec_paths}, indent=2, ensure_ascii=False))
PY
```
