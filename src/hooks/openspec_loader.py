#!/usr/bin/env python3
"""Lightweight openspec loader + auto-generator for ACE.

- Loads structured spec files (YAML/JSON or remote URL) with multiple profiles.
- Optionally auto-generates a draft spec from repo signals when none exists.
- Provides prompt-aware summarization for injection with graceful fallback.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from .utils.path_utils import get_project_dir, get_user_claude_dir, is_diagnostic_mode, save_diagnostic

DEFAULT_SPEC_FILENAME = "openspec.yaml"
CACHE_DIRNAME = "openspec-cache"
MAX_SPEC_ITEMS = 6
MAX_TEXT_BYTES = 120_000  # avoid huge files during auto generation


@dataclass
class SpecConfig:
    enable_spec_injection: bool = True
    enable_spec_auto_generate: bool = True
    spec_paths: List[str] = field(default_factory=list)
    default_profile: Optional[str] = "default"
    global_fallback_profile: Optional[str] = None
    spec_max_items: int = MAX_SPEC_ITEMS


def _env_flag(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val not in ("0", "false", "False", "")


def _build_config(settings: dict) -> SpecConfig:
    return SpecConfig(
        enable_spec_injection=_env_flag("ACE_OPENSPEC_ENABLE", settings.get("enable_spec_injection", True)),
        enable_spec_auto_generate=_env_flag("ACE_OPENSPEC_AUTOGEN", settings.get("enable_spec_auto_generate", True)),
        spec_paths=_resolve_spec_paths(settings),
        default_profile=os.getenv("ACE_OPENSPEC_PROFILE") or settings.get("default_profile") or "default",
        global_fallback_profile=settings.get("global_fallback_profile"),
        spec_max_items=int(os.getenv("ACE_OPENSPEC_MAX_ITEMS") or settings.get("spec_max_items") or MAX_SPEC_ITEMS),
    )


def _resolve_spec_paths(settings: dict) -> List[str]:
    env_paths = os.getenv("ACE_OPENSPEC_PATHS")
    if env_paths:
        return [p.strip() for p in env_paths.split(",") if p.strip()]

    paths = settings.get("spec_paths") or []
    if paths:
        return paths

    # Default: project-level openspec.yaml
    return [str(get_project_dir() / DEFAULT_SPEC_FILENAME)]


def _is_url(path: str) -> bool:
    parsed = urllib.parse.urlparse(path)
    return parsed.scheme in ("http", "https")


def _read_text(path: Path, max_bytes: int = MAX_TEXT_BYTES) -> Optional[str]:
    try:
        data = path.read_bytes()
        return data[:max_bytes].decode("utf-8", errors="ignore")
    except Exception:
        return None


def _load_remote(url: str) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            raw = resp.read()
            return raw[:MAX_TEXT_BYTES].decode("utf-8", errors="ignore")
    except Exception as e:  # pragma: no cover - network optional
        if is_diagnostic_mode():
            save_diagnostic(f"Failed to fetch remote spec {url}: {e}", "openspec_loader_remote")
        return None


def _load_single_spec(path: str) -> Tuple[Optional[dict], Optional[str]]:
    """Return (data, source)."""
    text = None
    source = None

    if _is_url(path):
        text = _load_remote(path)
        source = path
    else:
        p = Path(path).expanduser()
        if not p.exists():
            return None, None
        text = _read_text(p)
        source = str(p)

    if not text:
        return None, source

    data = None
    if path.endswith(".json"):
        try:
            data = json.loads(text)
        except Exception:
            data = None
    else:
        # Try YAML first (if available), then JSON fallback
        if yaml:
            try:
                data = yaml.safe_load(text)
            except Exception:
                data = None
        if data is None:
            try:
                data = json.loads(text)
            except Exception:
                data = None

    return data if isinstance(data, dict) else None, source


def _normalize_profile(profile: dict, source: str | None) -> dict:
    """Ensure key fields exist and attach provenance."""
    normalized = dict(profile)
    normalized.setdefault("goals", [])
    normalized.setdefault("requirements", [])
    normalized.setdefault("apis", [])
    normalized.setdefault("non_functional", [])
    normalized.setdefault("constraints", [])
    normalized.setdefault("acceptance", [])
    if source:
        normalized.setdefault("provenance", source)
    return normalized


def load_all(paths: List[str]) -> dict:
    """Load multiple spec files/URLs and merge profiles by name."""
    profiles: Dict[str, dict] = {}
    errors: List[str] = []

    for path in paths:
        data, source = _load_single_spec(path)
        if not data:
            continue

        profile_list = data.get("profiles") or []
        if isinstance(profile_list, dict):  # support dict form
            profile_list = list(profile_list.values())

        for profile in profile_list:
            if not isinstance(profile, dict):
                continue
            name = profile.get("name") or profile.get("id") or "default"
            normalized = _normalize_profile(profile, source)
            profiles[name] = normalized

    return {"profiles": profiles, "errors": errors}


def get_profile(loaded: dict, name: Optional[str]) -> Optional[dict]:
    if not loaded or "profiles" not in loaded:
        return None
    profiles = loaded["profiles"]
    if not profiles:
        return None
    if name and name in profiles:
        return profiles[name]
    # fallback to first profile
    first_name = next(iter(profiles.keys()))
    return profiles.get(first_name)


def _token_overlap_score(text: str, prompt: str) -> float:
    """Rough relevance score based on token overlap."""
    if not text or not prompt:
        return 0.0
    tokens_text = set(re.findall(r"[A-Za-z0-9_-]+", text.lower()))
    tokens_prompt = set(re.findall(r"[A-Za-z0-9_-]+", prompt.lower()))
    if not tokens_text or not tokens_prompt:
        return 0.0
    intersection = tokens_text & tokens_prompt
    return len(intersection) / max(len(tokens_prompt), 1)


def _collect_items(profile: dict) -> List[dict]:
    items: List[dict] = []

    def add(kind: str, text: str, priority: int = 0, confidence: float = 0.6, extra: Optional[dict] = None):
        if not text:
            return
        item = {
            "kind": kind,
            "text": text.strip(),
            "priority": priority,
            "confidence": confidence,
        }
        if extra:
            item.update(extra)
        items.append(item)

    for g in profile.get("goals", []) or []:
        add("goal", g, priority=3)
    for r in profile.get("requirements", []) or []:
        add("requirement", r, priority=2)
    for api in profile.get("apis", []) or []:
        if not isinstance(api, dict):
            add("api", str(api), priority=3)
            continue
        name = api.get("name") or ""
        method = api.get("method") or api.get("verb") or ""
        path = api.get("path") or api.get("url") or ""
        constraints = api.get("constraints") or api.get("notes") or ""
        text = f"{method} {path} {name}".strip()
        if constraints:
            text = f"{text} :: {constraints}"
        add("api", text, priority=4, extra={"path": path, "method": method})
    for nfr in profile.get("non_functional", []) or []:
        add("non_functional", nfr, priority=2)
    for c in profile.get("constraints", []) or []:
        add("constraint", c, priority=5)
    for acc in profile.get("acceptance", []) or []:
        add("acceptance", acc, priority=3)
    return items


def summarize_for_prompt(profile: dict, prompt: str, limit: int = MAX_SPEC_ITEMS) -> dict:
    items = _collect_items(profile)
    scored: List[dict] = []
    for item in items:
        relevance = _token_overlap_score(item.get("text", ""), prompt)
        scored.append({**item, "relevance": relevance})

    # Sort by relevance -> priority -> confidence
    scored.sort(key=lambda x: (x.get("relevance", 0), x.get("priority", 0), x.get("confidence", 0)), reverse=True)
    selected = scored[: max(limit, 1)]

    # Filter out low-signal items if we have better options
    if selected and selected[0]["relevance"] == 0:
        # No overlap, keep top N but mark as low confidence
        selected = selected[: max(min(3, limit), 1)]

    return {"items": selected}


def format_spec_context(profile_name: str, summary: dict) -> str:
    items = summary.get("items") or []
    if not items:
        return ""

    lines = [f"### 📜 Spec Context (profile: {profile_name})\n"]
    for item in items:
        kind = item.get("kind", "item")
        text = item.get("text", "")
        rel = item.get("relevance", 0)
        lines.append(f"- [{kind}] {text} (rel={rel:.2f})")
    return "\n".join(lines)


# ----------------------- Auto generation (draft) ----------------------- #

def _safe_glob(base: Path, patterns: List[str], limit: int = 50) -> List[Path]:
    found: List[Path] = []
    for pattern in patterns:
        for path in base.glob(pattern):
            found.append(path)
            if len(found) >= limit:
                return found
    return found


def _extract_from_readme(readme: Path) -> Tuple[List[str], List[str]]:
    goals: List[str] = []
    nfrs: List[str] = []
    text = _read_text(readme) or ""
    lines = text.splitlines()
    for line in lines[:200]:
        if line.strip().startswith(("#", "-", "*")):
            content = line.lstrip("#-* ").strip()
            if not content:
                continue
            if any(token in content.lower() for token in ["性能", "performance", "sla", "安全", "security", "可靠", "availability"]):
                nfrs.append(content)
            else:
                goals.append(content)
    return goals[:10], nfrs[:10]


def _extract_from_openapi(doc: dict) -> List[dict]:
    apis: List[dict] = []
    paths = doc.get("paths", {}) if isinstance(doc, dict) else {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, detail in methods.items():
            if not isinstance(detail, dict):
                continue
            name = detail.get("summary") or detail.get("operationId") or ""
            constraints = detail.get("description") or ""
            apis.append(
                {
                    "name": name,
                    "method": method.upper(),
                    "path": path,
                    "constraints": constraints[:200],
                }
            )
    return apis[:30]


def _load_possible_openapi(project_dir: Path) -> List[dict]:
    candidates = _safe_glob(project_dir, ["openapi*.yaml", "openapi*.yml", "openapi*.json", "swagger*.yaml", "swagger*.json"], limit=5)
    apis: List[dict] = []
    for candidate in candidates:
        text = _read_text(candidate)
        if not text:
            continue
        data = None
        if candidate.suffix == ".json":
            try:
                data = json.loads(text)
            except Exception:
                data = None
        else:
            if yaml:
                try:
                    data = yaml.safe_load(text)
                except Exception:
                    data = None
        if isinstance(data, dict):
            apis.extend(_extract_from_openapi(data))
    return apis


def _extract_from_tests(project_dir: Path) -> List[str]:
    tests = _safe_glob(project_dir, ["tests/**/*.py", "test_*.py", "*_test.py"], limit=10)
    acc: List[str] = []
    for t in tests:
        text = _read_text(t, max_bytes=30_000) or ""
        # crude extraction: look for test names
        for line in text.splitlines():
            if line.strip().startswith("def test_"):
                acc.append(line.strip().replace("def ", "").replace(":", ""))
                if len(acc) >= 20:
                    return acc
    return acc


def generate_spec_draft(project_dir: Path) -> Optional[dict]:
    """Best-effort, low-cost spec generation. Never raises."""
    goals: List[str] = []
    nfrs: List[str] = []
    requirements: List[str] = []
    constraints: List[str] = []
    acceptance: List[str] = []

    readmes = _safe_glob(project_dir, ["README*.md", "docs/**/*.md"], limit=5)
    if readmes:
        g, nf = _extract_from_readme(readmes[0])
        goals.extend(g)
        nfrs.extend(nf)

    apis = _load_possible_openapi(project_dir)

    acceptance.extend(_extract_from_tests(project_dir))

    # Heuristic constraints from package manifests
    pkg = project_dir / "package.json"
    if pkg.exists():
        constraints.append("Node project detected via package.json")
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        constraints.append("Python project detected via pyproject.toml")
    go_mod = project_dir / "go.mod"
    if go_mod.exists():
        constraints.append("Go project detected via go.mod")

    if not any([goals, requirements, apis, nfrs, constraints, acceptance]):
        return None

    return {
        "version": "0.1-auto",
        "profiles": [
            {
                "name": "default",
                "description": "Auto-generated draft spec",
                "goals": goals[:10],
                "requirements": requirements[:20],
                "apis": apis[:20],
                "non_functional": nfrs[:10],
                "constraints": constraints[:10],
                "acceptance": acceptance[:10],
                "provenance": "auto-generated",
                "confidence": 0.6,
            }
        ],
    }


def _cache_path(project_dir: Path) -> Path:
    safe_name = project_dir.name or "default"
    return get_user_claude_dir() / CACHE_DIRNAME / safe_name / DEFAULT_SPEC_FILENAME


def _persist_cache(data: dict, project_dir: Path) -> Optional[Path]:
    try:
        target = _cache_path(project_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Prefer YAML if available; otherwise JSON
        if yaml:
            serialized = yaml.safe_dump(data, allow_unicode=True)
        else:
            serialized = json.dumps(data, indent=2, ensure_ascii=False)
        target.write_text(serialized, encoding="utf-8")
        return target
    except Exception:
        return None


def load_or_generate(paths: List[str], config: SpecConfig) -> dict:
    loaded = load_all(paths)
    if loaded.get("profiles"):
        return loaded

    if not config.enable_spec_auto_generate:
        return loaded

    project_dir = get_project_dir()
    generated = generate_spec_draft(project_dir)
    if not generated:
        return loaded

    persisted = _persist_cache(generated, project_dir)
    if persisted:
        cache_loaded = load_all([str(persisted)])
        return cache_loaded
    return {"profiles": {p.get("name", "default"): _normalize_profile(p, "auto-generated") for p in generated.get("profiles", [])}}


# ----------------------- Public entry point ----------------------- #

def get_spec_context(prompt_text: str, settings: dict) -> dict:
    config = _build_config(settings or {})
    if not config.enable_spec_injection:
        return {"context": "", "meta": {"reason": "disabled"}}

    loaded = load_or_generate(config.spec_paths, config)
    profile = get_profile(loaded, config.default_profile)
    if not profile and config.global_fallback_profile:
        profile = get_profile(loaded, config.global_fallback_profile)

    if not profile:
        return {"context": "", "meta": {"reason": "no_profile"}}

    summary = summarize_for_prompt(profile, prompt_text, limit=config.spec_max_items)
    context = format_spec_context(profile.get("name", "default"), summary)

    meta = {
        "profile": profile.get("name", "default"),
        "items": len(summary.get("items", [])),
        "paths": config.spec_paths,
    }

    if is_diagnostic_mode():
        save_diagnostic(
            json.dumps(
                {
                    "prompt_preview": prompt_text[:200],
                    "summary_items": summary.get("items", []),
                    "meta": meta,
                },
                ensure_ascii=False,
                indent=2,
            ),
            "openspec_loader",
        )

    return {"context": context, "meta": meta}
