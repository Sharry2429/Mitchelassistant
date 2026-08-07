"""
mitchell.core.review
====================
Phase 11 — Review pipeline as a configured workflow over the routing table.

Runs against real code/diff: a CHEAP model ("mid") reviews iteratively in a
loop until it stops finding issues (capped), then ONE expensive "top" (Sol)
call does the final high-stakes pass, then flagged issues become fix tasks
dispatched back through the executor. This operationalizes the
Luna-iterative -> Sol-final -> fixes workflow.
"""
from __future__ import annotations

import uuid

from mitchell.core.llm_client import call


async def iterative_review(text: str, tier: str = "mid", max_iter: int = 3, llm_call=None) -> list[str]:
    """Cheap model in a loop until NO_ISSUES or the iteration cap. Returns issue blobs."""
    inject = llm_call or call
    issues: list[str] = []
    for _ in range(max_iter):
        r = await inject(tier, messages=[{"role": "user", "content":
            f"Review the following for bugs and improvements. Reply with concrete "
            f"issues as a numbered list, or exactly NO_ISSUES if none.\n\n{text}"}], task_id="review")
        out = (r.content or "").strip()
        if not out or "NO_ISSUES" in out.upper():
            break
        issues.append(out)
    return issues


async def final_review(text: str, tier: str = "top", llm_call=None) -> str:
    """ONE expensive final pass; returns the verdict + any remaining issues."""
    inject = llm_call or call
    r = await inject(tier, messages=[{"role": "user", "content":
        f"This passed iterative review. Do a final high-stakes pass and report any "
        f"remaining issues or APPROVED.\n\n{text}"}], task_id="review-final")
    return (r.content or "").strip()


async def apply_fixes(issues: list[str], prefix: str = "rx") -> list[str]:
    """Turn flagged issues into fix tasks in the queue. Returns their ids."""
    from mitchell.core.tasks import Task, TaskState
    ids = []
    for it in issues:
        t = Task(id=f"{prefix}-{uuid.uuid4().hex[:6]}", instruction=f"Fix review issue: {it}")
        t.state = TaskState.PENDING
        t.save()
        ids.append(t.id)
    return ids


async def run_review(text: str, llm_call=None) -> dict:
    """Full pipeline: iterative (mid) -> final (top) -> fix tasks."""
    iterative = await iterative_review(text, llm_call=llm_call)
    final = await final_review(text, llm_call=llm_call)
    flags = [i for i in iterative] + ([final] if final and "APPROVED" not in final.upper() else [])
    fix_ids = await apply_fixes(flags)
    return {"iterative_issues": iterative, "final": final, "fix_task_ids": fix_ids}
