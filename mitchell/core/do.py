"""
mitchell.core.do
================
Rapid fast interface. Usage:

    mitchell-do "open example.com and tell me the title"
    mitchell-do "implement a fibonacci function in this repo"
    mitchell-do "check the android battery"

Routing (fast, no prompts):
  * coding intent  -> delegate to Hermes-Agent subprocess in an isolated
                      workdir (HermesCoder), then verify (run pytest if a test
                      was produced).
  * else (browser / Windows / Android) -> Mitchell's plan-execute-verify loop
                      over the REAL safe tool surface, timed.

Everything is measured (wall-clock) and reported. Nothing faked.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

from mitchell.core.safe_provider import SafeProvider
from mitchell.core.tasks import Task, TaskState

_CODING_WORDS = (
    "implement", "write a function", "write a script", "write code", "write a module",
    "add function", "add a function", "refactor", "fix bug", "fix this code",
    "create a class", "new function", "unit test", "pytest", "make a program",
    "coding task", "develop", "codebase", "function that", "script that",
)


def _is_coding(task: str) -> bool:
    low = task.lower()
    return any(w in low for w in _CODING_WORDS)


def _run_coding(task: str, timeout: int = 900) -> dict:
    from mitchell.coding.hermes_coder import run_hermes_code
    res = run_hermes_code(task, timeout=timeout)
    # Ground-truth verification: if hermes produced a pytest test, run it.
    verify = "no test produced"
    if res.get("ok"):
        wd = res["workdir"]
        test_files = [l for l in (res["files"] or "").splitlines() if "test" in l.lower() and l.strip().endswith(".py")]
        if test_files:
            import subprocess
            r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=wd, capture_output=True, text=True, timeout=180)
            tail = (r.stdout.strip().splitlines() or [""])[-1]
            verify = f"pytest: {tail} (exit={r.returncode})"
    res["verify"] = verify
    return res


async def _run_agent(task: str, idx: str) -> dict:
    provider = SafeProvider()
    t = Task(id=idx, instruction=task)
    t.state = TaskState.PENDING
    t.save()
    from mitchell.core.executor import execute_task
    t0 = time.monotonic()
    try:
        await execute_task(t.id, tools=provider)
    except Exception as e:  # noqa: BLE001
        dt = round(time.monotonic() - t0, 2)
        return {"ok": False, "duration": dt, "error": f"{type(e).__name__}: {e}", "state": "error"}
    dt = round(time.monotonic() - t0, 2)
    final = Task.load(t.id)
    return {"ok": final.state == TaskState.COMPLETED, "duration": dt, "state": final.state,
            "steps": len(final.steps),
            "steps_ok": sum(1 for s in final.steps if s.state == TaskState.COMPLETED)}


async def _run_fast(task: str, idx: str) -> dict:
    """Lightning-fast path (1-2 LLM round trips) over safe real tools."""
    from mitchell.core.fast import fast_do
    provider = SafeProvider()
    t0 = time.monotonic()
    try:
        res = await fast_do(task, provider)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "answer": f"{type(e).__name__}: {e}",
                "elapsed": round(time.monotonic() - t0, 2), "fast": True}
    return {"ok": bool(res.get("answer") and res.get("answer").strip()),
            "answer": res.get("answer"), "tool": res.get("tool"),
            "elapsed": res.get("elapsed") or round(time.monotonic() - t0, 2), "fast": True}


def main():
    if len(sys.argv) < 2:
        print("usage: mitchell-do \"<task>\"")
        sys.exit(2)
    task = " ".join(sys.argv[1:])
    print(f"mitchell do: {task}")
    t0 = time.monotonic()

    if _is_coding(task):
        res = _run_coding(task)
        print(f"\n[CODING] delegated to Hermes subprocess")
        print(f"  exit={res.get('exit_code')} duration={res['duration']}s workdir={res.get('workdir')}")
        print(f"  files:\n{res.get('files','')}")
        print(f"  verify: {res.get('verify')}")
        if not res.get('ok'):
            print(f"  stderr tail: {(res.get('stderr_tail') or '')[-400:]}")
        sys.exit(0 if res.get('ok') else 3)
    else:
        print("\n[browser/Windows/Android — fast path]")
        res = asyncio.get_event_loop().run_until_complete(_run_fast(task, "fast-"))
        print(f"  fast: {res.get('fast')} tool={res.get('tool')} duration={res.get('elapsed')}s")
        print(f"\n  ANSWER: {(res.get('answer') or '').strip()[:800]}")
        # If the fast path couldn't produce an answer, fall back to the full loop.
        if not res.get("ok"):
            print("\n  fast path produced no answer -> running full verified loop...")
            res = asyncio.get_event_loop().run_until_complete(_run_agent(task, f"do-{uuid.uuid4().hex[:8]}"))
            print(f"  [full loop] state={res.get('state')} duration={res.get('duration')}s "
                  f"steps={res.get('steps')} (ok={res.get('steps_ok')})")
            sys.exit(0 if res.get("ok") else 4)
        else:
            sys.exit(0)

    print(f"\n  total wall-clock: {round(time.monotonic()-t0,2)}s")


if __name__ == "__main__":
    main()
