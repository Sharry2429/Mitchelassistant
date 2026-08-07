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
