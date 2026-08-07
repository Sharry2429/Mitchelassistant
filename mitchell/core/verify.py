"""
mitchell.core.verify
====================
Layered verification for agent steps (Phase 1).

Level 0 – runs/compiles: the step produced actual output and no tool errored.
Level 1 – real assertions: environment-level checks declared on the step
          (e.g. ``expect_file_exists``, ``expect_process_running``), driven by
          actual tool results — NOT agent-authored test claims.

This module is the seam that makes verification a hard gate. The executor calls
``verify_step`` unconditionally (import here at module load), so a missing
implementation is an ImportError at startup — never a silent pass-through.
"""
from __future__ import annotations

import os
from typing import Any

from mitchell.core.result import MCPResult

# The executor depends on this symbol existing; if it is ever removed, importing
# the executor fails loudly instead of silently trusting every step.
__all__ = ["verify_step", "verify_file_exists", "verify_process_running"]


def verify_file_exists(path: str) -> MCPResult:
    if os.path.exists(os.path.expanduser(path)):
        return MCPResult.success(data=f"File {path} exists.")
    return MCPResult.fail(error=f"File {path} does not exist.")


def verify_process_running(process_name: str) -> MCPResult:
    import psutil

    for p in psutil.process_iter(["name"]):
        if p.info["name"] == process_name:
            return MCPResult.success(data=f"Process {process_name} is running.")
    return MCPResult.fail(error=f"Process {process_name} is not running.")


def _last_assistant_text(messages: list[dict]) -> str:
    """Return the text of the final assistant message, or ''."""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                ]
                return "\n".join(parts)
    return ""


def _any_tool_error(messages: list[dict]) -> bool:
    """True if any tool result in the transcript was an execution error."""
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content") or ""
            if isinstance(content, str) and content.startswith("Error executing tool"):
                return True
    return False


def verify_step(step: Any, messages: list[dict]) -> bool:
    """Verify a single completed step against Levels 0–1.

    Returns True only if the step demonstrably did what it claimed:
      * L0 — final assistant output is non-empty and no tool errored.
      * L1 — any environment assertion declared on the step's args holds
             (real file/process checks against the actual machine).

    Fails closed: any doubt, ANY unexpected condition, returns False (the
    step is recorded FAILED and retried by the executor).
    """
    # --- Level 0: the step actually ran and produced output, error-free ---
    if not _last_assistant_text(messages).strip():
        return False
    if _any_tool_error(messages):
        return False

    # --- Level 1: real, environment-grounded assertions (not LLM claims) ---
    args = (step.args or {}) if hasattr(step, "args") else {}

    expect_file = args.get("expect_file_exists")
    if expect_file:
        if not verify_file_exists(str(expect_file)).ok:
            return False

    expect_proc = args.get("expect_process_running")
    if expect_proc:
        if not verify_process_running(str(expect_proc)).ok:
            return False

    return True


# ------------------------- Levels 2-4 (Phase 1) ---------------------------

def _transcript_text(transcript: list[dict]) -> str:
    parts = []
    for m in transcript or []:
        c = m.get("content", "")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            parts.append(" ".join(x.get("text", "") for x in c if isinstance(x, dict)))
    return "\n".join(parts)


def verify_against_rubric(step: Any, transcript: list[dict], rubric: list[str]) -> dict:
    """Level 2 — completion against a pre-written rubric (not agent-authored tests).

    Scores the transcript against the rubric; passes at >= 0.5 coverage.
    """
    if not rubric:
        return {"score": 0.0, "passed": False, "matched": [], "missing": []}
    text = _transcript_text(transcript).lower()
    matched = [r for r in rubric if r.lower() in text]
    score = len(matched) / len(rubric)
    return {"score": round(score, 2), "passed": score >= 0.5,
            "matched": matched, "missing": [r for r in rubric if r.lower() not in text]}


async def adversarial_review(transcript: list[dict], llm_call=None) -> tuple[bool, list[str]]:
    """Level 3 — one cross-model adversarial review. Returns (passed, issues).

    A different (top-tier) model scrutinizes the execution; APPROVED = pass,
    anything else is treated as issues that fail the step.
    """
    from mitchell.core.llm_client import call as _default_call
    inject = llm_call or _default_call
    text = _transcript_text(transcript)
    r = await inject("top", messages=[{"role": "user", "content":
        f"Adversarially review this execution for hidden bugs or wrong results. "
        f"Reply exactly APPROVED if sound, else list concrete issues.\n\n{text}"}],
        task_id="adversarial")
    out = (r.content or "").strip()
    if "APPROVED" in out.upper():
        return True, []
    issues = [l.strip(" -•\t") for l in out.splitlines() if l.strip() and not l.strip().upper().startswith("APPROVED")]
    return False, issues


def device_verify(step: Any, expected_foreground: str | None = None) -> bool:
    """Level 4 — live/device verification for behavioral steps.

    For Android steps, re-reads the actual foreground app from the device and
    compares it to what the step claims, instead of trusting the narration.
    Returns False when the live device does not match expectation.
    """
    args = (step.args or {}) if hasattr(step, "args") else {}
    if expected_foreground is None:
        expected_foreground = args.get("expect_foreground_app")
    if not expected_foreground:
        return True  # nothing device-specific to assert -> vacuously pass
    try:
        import asyncio

        async def _get():
            from mitchell.mcp_server import mcp
            resp = await mcp.call_tool("android_apps_get_foreground_app", arguments={})
            texts = [c.text for c in resp if hasattr(c, "text")]
            return "\n".join(texts) if texts else str(resp)

        actual = asyncio.run(_get())
        return expected_foreground.lower() in actual.lower()
    except Exception:  # noqa: BLE001 - cannot reach device -> fail closed
        return False
