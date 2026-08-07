"""
mitchell.core.tool_registry
===========================
Phase 5 — Tool Foundry.

Mitchell notices a capability gap (a repeated step in its episodic log that it
keeps hand-rolling), DRAFTS a tool for it via the Hermes-Agent coding worker,
TESTS it through Phase 1 verification, and only then REGISTERS it so future
tasks can call it. An untested self-made tool is worse than none, so the test
gate is structural: no tool enters the live registry until its own test passes.

Lifecycle: detect_gap -> draft_tool -> test_tool -> register_tool -> callable.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from mitchell.core import memory

FOUNDRY_DIR = Path(os.path.expanduser("~/.system-mcp/foundry"))
REGISTRY_FILE = FOUNDRY_DIR / "registry.json"


# ---- detect: a repeated capability gap in the episodic log -----------------

def detect_gap(min_freq: int = 3, known: tuple[str, ...] = ()) -> str | None:
    """Return the most frequent repeated step pattern that isn't a known tool.

    A step pattern recursing many times in the ground-truth log is a capability
    Mitchell keeps having to re-derive by hand -> draft a tool for it.
    """
    counts: Counter = Counter()
    for ep in memory.list_episodes(kind="step"):
        pk = ep.get("pattern_key")
        if pk and all(k not in (pk or "") for k in known):
            counts[pk] += 1
    if not counts:
        return None
    top, n = counts.most_common(1)[0]
    return top if n >= min_freq else None


# ---- draft: have the Hermes coding worker write the tool -------------------

def draft_tool(spec: str, timeout: int = 900) -> dict:
    """Delegate tool-drafting to the Hermes coding worker in an isolated dir."""
    from mitchell.coding.hermes_coder import run_hermes_code
    return run_hermes_code(spec, timeout=timeout)


# ---- test: Phase 1 verification gate (real assertions, not author's word) --

def test_tool(workdir: str) -> dict:
    """Run the drafted tool's own test under pytest. Gate on exit 0 + pass."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workdir, capture_output=True, text=True, timeout=240,
    )
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return {"ok": r.returncode == 0, "result": tail, "exit": r.returncode}


# ---- register: only a tested tool enters the live registry -----------------

def register_tool(name: str, src_dir: str, spec: str) -> str | None:
    """Register a tool ONLY after its test passes. Returns name or None.

    The Phase 1 gate is enforced here structurally: no tool enters the live
    registry unless a real pytest run over its own test is green.
    """
    if not test_tool(src_dir)["ok"]:
        return None
    FOUNDRY_DIR.mkdir(parents=True, exist_ok=True)
    dst = FOUNDRY_DIR / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src_dir, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    registry: dict = {}
    if REGISTRY_FILE.exists():
        registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    registry[name] = {"spec": spec, "src": str(dst), "registered_at": __import__("time").time()}
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return name


def list_registered() -> list[str]:
    if not REGISTRY_FILE.exists():
        return []
    return list(json.loads(REGISTRY_FILE.read_text(encoding="utf-8")))


def load_foundry_function(name: str):
    """Import and return the callable for a registered foundry tool."""
    path = FOUNDRY_DIR / name / "tool.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"foundry.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, name, None)
