"""
scripts/prove_memory.py — Phase 3 exit conditions, runnable as:

    python scripts/prove_memory.py

Demonstrates, with real output:
  A. Episodic + semantic + procedural stores behave correctly.
  B. Learning mechanic: verified episodes promote to a procedural skill doc;
     an unverified episode blocks its cluster (verification gated BY CONSTRUCTION).
  C. Interrupt recovery: a task killed mid-step resumes and completes — it does
     NOT start cold, and the interruption lands in the ground-truth log.
"""
import asyncio
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitchell.core import memory, memory_store  # noqa: E402
from mitchell.core.executor import recover_interrupted_tasks, worker_loop  # noqa: E402
from mitchell.core.tasks import Task, TaskState, TaskStep  # noqa: E402
from mitchell.core.tool_provider import StaticToolProvider  # noqa: E402
from tests.helpers import make_fake_llm  # noqa: E402

BANNER = "=" * 62


def show(t): print(f"\n{BANNER}\n{t}\n{BANNER}")


def main():
    # Isolate to a throwaway DB so we don't touch real memory.
    from pathlib import Path as _Path
    tmp = _Path(tempfile.mkdtemp(prefix="mitchell-memory-proof-"))
    memory_store.MEMORY_DIR = tmp
    memory_store.DB_PATH = tmp / "mitchell.db"
    memory_store.init_db()
    show(f"isolated memory DB -> {memory_store.DB_PATH}")

    # ---- A: the three stores ----
    memory.log_episode("t0", "step", "PASS step: bootstrap", verified=True, pattern_key="bootstrap")
    memory.remember_semantic("device.os", "windows")
    memory.save_schema("Skill: echo", "return input untouched", verified=True)
    print("episodic rows:", len(memory.list_episodes()))
    print("semantic fact device.os:", memory.recall_semantic("device.os"))
    print("schema retrievable for 'echo input':",
          memory.retrieve_schema("echo input") is not None)

    # ---- B: promotion gated on verification ----
    show("B. learning mechanic: verified episodes -> procedural doc")
    for _ in range(3):
        memory.log_episode("t1", "step", "PASS step: sync device time",
                           verified=True, pattern_key="sync_time")
    promoted = memory.promote_verified_patterns(min_occurrences=3)
    print("promoted titles:", promoted)
    hit = memory.retrieve_schema("sync device time")
    print("retrievable before a future task:", hit is not None)

    # unverified blocks promotion
    for _ in range(2):
        memory.log_episode("t2", "step", "PASS step: reformat code",
                           verified=True, pattern_key="reformat_code")
    memory.log_episode("t2", "step", "FAIL step: reformat code",
                       verified=False, pattern_key="reformat_code")
    memory.promote_verified_patterns(min_occurrences=2)
    unverified_promoted = [s["title"] for s in memory.list_schemas(verified=True)
                           if "reformat" in s["title"]]
    print("unverified 'reformat' cluster promoted?", unverified_promoted, "(must be [] — blocked)")

    # ---- C: resume after kill ----
    show("C. interrupt recovery: killed mid-task -> resumes, not cold")
    tid = str(uuid.uuid4())
    task = Task(id=tid, instruction="resumable task")
    task.state = TaskState.RUNNING
    task.steps = [
        TaskStep(description="step one", action="skills.echo", state=TaskState.COMPLETED),
        TaskStep(description="step two", action="skills.echo", state=TaskState.RUNNING,
                 claimed_by="w-killed", claimed_at=1.0),
        TaskStep(description="step three", action="skills.echo", state=TaskState.PENDING),
    ]
    task.save()
    print("before recovery, step two state:", Task.load(tid).steps[1].state)

    n = recover_interrupted_tasks()
    print(f"recovered {n} interrupted task(s)")
    t = Task.load(tid)
    print("after recovery, step two state:", t.steps[1].state, "(PENDING -> reclaimable)")

    asyncio.get_event_loop().run_until_complete(
        worker_loop("w-new", "worker-general", tid,
                    tools=StaticToolProvider(), llm_call=make_fake_llm(final_text="ok"))
    )
    final = Task.load(tid)
    print("resumed task final state:", final.state)
    kinds = {e["kind"] for e in memory.list_episodes()}
    print("interruption recorded in ground-truth log:", "interrupt" in kinds)

    ok = hit and not unverified_promoted and final.state == TaskState.COMPLETED and "interrupt" in kinds
    print("\n=== MEMORY PROOF:", "PASS" if ok else "CHECK", "===")


if __name__ == "__main__":
    main()
