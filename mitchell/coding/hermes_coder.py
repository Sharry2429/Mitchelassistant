"""
mitchell.coding.hermes_coder
============================
Hermes-Agent is the coding worker for Mitchell (replaces the OpenCode idea —
fully integrated).

Mitchell dispatches a coding sub-task by spawning a `hermes chat -q` subprocess
inside an ISOLATED, git-inited workdir. Hermes writes the code; Mitchell then
captures the produced files/diff and hands them to Phase 1 verification. Each
coding run is self-contained and revertible (a git repo with a clean base), so
nothing Hermes writes reaches the real tree until Mitchell verifies and commits.

The result is a dict with ground-truth handles (workdir, git status, duration,
subprocess exit) so callers can verify what actually happened — never a
self-reported "it worked."
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import uuid

_CODE_ROOT = os.path.expanduser("~/.system-mcp/coding")


def _fresh_workdir() -> str:
    os.makedirs(_CODE_ROOT, exist_ok=True)
    wd = os.path.join(_CODE_ROOT, uuid.uuid4().hex[:8])
    os.makedirs(wd, exist_ok=True)
    # Seed a git repo with an empty base so diffs/labels are meaningful.
    subprocess.run(["git", "init", "-q"], cwd=wd, capture_output=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "base"], cwd=wd, capture_output=True)
    return wd


def run_hermes_code(
    spec: str,
    workdir: str | None = None,
    timeout: int = 900,
    model: str | None = None,
) -> dict:
    """Dispatch a coding sub-task to a Hermes-Agent subprocess.

    Returns a dict:
        ok            subprocess completed (exit 0)
        exit_code     hermes process return code
        duration      wall-clock seconds
        files         git status --short (files hermes created/modified)
        diff_stat     git diff --stat after staging
        stdout_tail   tail of hermes stdout
        workdir       isolated dir the code lives in (for verification/commit)
    """
    wd = workdir or _fresh_workdir()
    spec_file = os.path.join(wd, "TASK.md")
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write("You are being asked by the Mitchell agent to do a coding sub-task.\n\n" + spec + "\n")

    argv = ["hermes", "--yolo", "chat", "-q",
            f"Read TASK.md in this directory and implement it exactly. Edit files directly. "
            f"Add a test for what you write and run it; report the result."]
    if model:
        argv = ["hermes", "--yolo", "-m", model, "chat", "-q", argv[-1]]

    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=wd, capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0
        err = proc.stderr[-3000:]
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": None, "duration": round(time.monotonic() - t0, 2),
                "error": f"hermes timed out after {timeout}s", "workdir": wd}
    duration = round(time.monotonic() - t0, 2)

    # Stage everything and diff to capture created+modified files.
    subprocess.run(["git", "add", "-A"], cwd=wd, capture_output=True)
    status = subprocess.run(["git", "status", "--short"], cwd=wd, capture_output=True, text=True).stdout
    diffstat = subprocess.run(["git", "diff", "--cached", "--stat"], cwd=wd, capture_output=True, text=True).stdout

    return {
        "ok": ok,
        "exit_code": proc.returncode,
        "duration": duration,
        "files": status,
        "diff_stat": diffstat,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": err or None,
        "workdir": wd,
    }
