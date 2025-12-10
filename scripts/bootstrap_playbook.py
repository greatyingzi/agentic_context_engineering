#!/usr/bin/env python3
"""Bootstrap playbook.json from historical Claude transcripts."""

import argparse
import asyncio
from datetime import datetime
import os
import sys
from pathlib import Path

# Allow importing the existing hook utilities (works in-repo and after install to ~/.claude).
REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (
    REPO_ROOT,
    REPO_ROOT / "src",
    REPO_ROOT / "hooks",  # when installed under ~/.claude/hooks
):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Try repo-style import first; fall back to installed hooks path.
try:
    from src.hooks.common import (  # type: ignore  # noqa: E402
        extract_keypoints,
        is_diagnostic_mode,
        load_playbook,
        load_transcript,
        save_playbook,
        save_diagnostic,
        update_playbook_data,
        load_settings,
    )
    # Import document and Git scanners
    from src.hooks.document_scanner import extract_document_knowledge
    from src.hooks.git_scanner import extract_git_knowledge
except ModuleNotFoundError:
    from hooks.common import (  # type: ignore  # noqa: E402
        extract_keypoints,
        is_diagnostic_mode,
        load_playbook,
        load_transcript,
        save_playbook,
        save_diagnostic,
        update_playbook_data,
        load_settings,
    )
    from hooks.document_scanner import extract_document_knowledge
    from hooks.git_scanner import extract_git_knowledge

ENV_FILE = Path.home() / ".claude" / "env"


def load_env_file():
    """Load KEY=VAL lines from ~/.claude/env if present (silent on errors)."""
    if not ENV_FILE.exists():
        return
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        # best-effort; ignore any parsing issues
        pass


def normalize_env(default_model: str = "glm-4.6"):
    """Normalize AGENTIC_* and ANTHROPIC_* env for the SDK."""
    api_key = (
        os.getenv("AGENTIC_CONTEXT_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
    )
    base_url = os.getenv("AGENTIC_CONTEXT_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")
    model = (
        os.getenv("AGENTIC_CONTEXT_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or default_model
    )

    if api_key:
        os.environ["AGENTIC_CONTEXT_API_KEY"] = api_key
        os.environ["ANTHROPIC_API_KEY"] = api_key
    if base_url:
        os.environ["AGENTIC_CONTEXT_BASE_URL"] = base_url
        os.environ["ANTHROPIC_BASE_URL"] = base_url
    os.environ["AGENTIC_CONTEXT_MODEL"] = model
    os.environ["ANTHROPIC_MODEL"] = model
    os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model


def derive_history_dir(project_dir: Path) -> Path:
    """Pick a history dir under ~/.claude/projects.

    Priority:
    1) ~/.claude/projects/-<project_dir> if it exists
    2) Any dir under ~/.claude/projects containing *.jsonl, preferring name containing project_dir.name
    3) Fallback to the default path (may not exist; caller will error with a hint)
    """
    base = Path.home() / ".claude" / "projects"
    base.mkdir(parents=True, exist_ok=True)

    safe = str(project_dir).replace("/", "-")
    default_path = base / safe
    if default_path.exists():
        return default_path

    candidates = [p for p in base.iterdir() if p.is_dir() and any(p.glob("*.jsonl"))]
    if not candidates:
        return default_path

    proj_name = project_dir.name
    named = [p for p in candidates if proj_name in p.name]
    if named:
        return sorted(named, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def prune_diagnostics(diag_dir: Path, keep: int = 20):
    """Keep only the most recent `keep` diagnostic files."""
    try:
        files = sorted(
            diag_dir.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[keep:]:
            old.unlink(missing_ok=True)
    except Exception:
        pass


async def bootstrap_playbook(
    history_dir: Path,
    project_dir: Path,
    limit: int,
    force: bool,
    diagnostic_name: str,
    order: str,
):
    """Replay transcripts to build the playbook."""
    # Always use absolute paths to avoid surprises.
    history_dir = history_dir.expanduser().resolve()
    project_dir = project_dir.expanduser().resolve()

    os.environ["CLAUDE_PROJECT_DIR"] = str(project_dir)

    diag_lines: list[str] = []
    diagnostic_enabled = is_diagnostic_mode()
    diag_file: Path | None = None

    if diagnostic_enabled:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diag_dir = project_dir / ".claude" / "diagnostic"
        diag_dir.mkdir(parents=True, exist_ok=True)
        diag_file = diag_dir / f"{timestamp}_{diagnostic_name}.txt"

    def flush_diag():
        if not diagnostic_enabled or diag_file is None:
            return
        try:
            diag_file.write_text("\n".join(diag_lines), encoding="utf-8")
        except Exception:
            pass

    def diag(msg: str):
        if not diagnostic_enabled:
            return
        diag_lines.append(msg)
        flush_diag()

    playbook = (
        {"version": "1.0", "last_updated": None, "key_points": []}
        if force
        else load_playbook()
    )

    jsonl_files = sorted(
        history_dir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=(order == "newest"),
    )
    if limit and limit > 0:
        jsonl_files = jsonl_files[:limit]

    processed = 0
    new_points = 0
    start_msg = (
        f"[start] history_dir={history_dir}, project_dir={project_dir}, "
        f"files={len(jsonl_files)}, limit={limit}, force={force}, order={order}"
    )
    print(start_msg)
    if diagnostic_enabled:
        diag(start_msg)
        if jsonl_files:
            diag(f"[order] first={jsonl_files[0].name}, last={jsonl_files[-1].name}")

    for transcript_path in jsonl_files:
        try:
            print(f"[processing] {transcript_path.name} …")
            messages = load_transcript(str(transcript_path))
            if not messages:
                diag(f"[skip-empty] {transcript_path.name}")
                print(f"[skip-empty] {transcript_path.name}")
                continue

            before = len(playbook.get("key_points", []))
            extraction_result = await extract_keypoints(
                messages, playbook, diagnostic_name
            )
            playbook = update_playbook_data(playbook, extraction_result)
            after = len(playbook.get("key_points", []))

            # Persist after each transcript to avoid losing progress on later failures.
            save_playbook(playbook)

            processed += 1
            new_points += max(after - before, 0)
            msg_ok = f"[ok] {transcript_path.name}: +{after - before} (total={after})"
            print(msg_ok)
            diag(msg_ok)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[warn] failed on {transcript_path.name}: {exc}", file=sys.stderr)
            diag(f"[warn] {transcript_path.name}: {exc}")
            continue

    # After processing transcripts, extract additional knowledge from documents and Git
    print("\n[info] Extracting knowledge from documents and Git history...")

    # Load settings to check what scanning is enabled
    settings = load_settings()

    # Extract knowledge from documents if enabled
    if settings.get("document_scanning_enabled", False):
        print("[scanning] Extracting knowledge from project documents...")
        doc_result = await extract_document_knowledge(playbook)
        doc_points = doc_result.get("new_key_points", [])

        if doc_points:
            playbook = update_playbook_data(playbook, doc_result)
            new_points += len(doc_points)
            print(f"[ok] extracted {len(doc_points)} key points from documents")
            if diagnostic_enabled:
                diag(f"[documents] extracted {len(doc_points)} key points")

    # Extract knowledge from Git history if enabled
    if settings.get("git_scanning_enabled", False):
        print("[scanning] Extracting knowledge from Git history...")
        git_result = await extract_git_knowledge(playbook)
        git_points = git_result.get("new_key_points", [])

        if git_points:
            playbook = update_playbook_data(playbook, git_result)
            new_points += len(git_points)
            print(f"[ok] extracted {len(git_points)} key points from Git history")
            if diagnostic_enabled:
                diag(f"[git] extracted {len(git_points)} key points")

    save_playbook(playbook)
    summary = (
        f"[done] processed={processed}, added≈{new_points}, "
        f"total={len(playbook.get('key_points', []))}"
    )
    print(summary)
    print(f"[success] bootstrap complete: processed={processed}, total_kpts={len(playbook.get('key_points', []))}")

    if diagnostic_enabled:
        diag(summary)
        try:
            if diag_file:
                diag_file.write_text("\n".join(diag_lines), encoding="utf-8")
                print(f"[info] diagnostic written: {diag_file}")
                prune_diagnostics(diag_file.parent)
        except Exception:
            pass

    print(
        f"Processed {processed} transcripts, added ~{new_points} key points, "
        f"total key points: {len(playbook.get('key_points', []))}."
    )
    print("\n[info] Knowledge extraction summary:")
    print("  - Historical conversations: ✓")
    if settings.get("document_scanning_enabled", False):
        print("  - Project documents: ✓")
    else:
        print("  - Project documents: ✗ (disabled)")
    if settings.get("git_scanning_enabled", False):
        print("  - Git history: ✓")
    else:
        print("  - Git history: ✗ (disabled)")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bootstrap playbook.json from Claude history jsonl files."
    )
    parser.add_argument(
        "--history-dir",
        required=False,
        type=Path,
        help="Directory under ~/.claude/projects containing *.jsonl history (default derives from project).",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project root whose .claude/playbook.json will be written (default: CWD).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of transcripts to replay (oldest first).",
    )
    parser.add_argument(
        "--order",
        type=str,
        default="oldest",
        choices=["oldest", "newest"],
        help="Processing order for transcripts (default: oldest).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Start from an empty playbook instead of merging with existing.",
    )
    parser.add_argument(
        "--diagnostic-name",
        type=str,
        default="history_bootstrap",
        help="Diagnostic name for saved prompts/responses when diagnostic mode is on.",
    )
    return parser.parse_args()


def main():
    load_env_file()
    normalize_env()

    args = parse_args()

    # Resolve to absolute paths early.
    project_dir = (args.project_dir or Path.cwd()).expanduser().resolve()
    history_dir = (
        args.history_dir.expanduser().resolve()
        if args.history_dir
        else derive_history_dir(project_dir)
    )

    args.history_dir = history_dir
    args.project_dir = project_dir

    if not args.history_dir.exists():
        print(
            f"[error] history dir not found: {args.history_dir}\n"
            f"hint: set ACE_HISTORY_DIR to an existing directory under ~/.claude/projects containing *.jsonl",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(
        bootstrap_playbook(
            history_dir=args.history_dir,
            project_dir=args.project_dir,
            limit=args.limit,
            force=args.force,
            diagnostic_name=args.diagnostic_name,
            order=args.order,
        )
    )


if __name__ == "__main__":
    main()


