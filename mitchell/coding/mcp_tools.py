"""
mitchell.coding.mcp_tools
=========================
Exposes the Hermes coding worker as an MCP tool so Mitchell's executor can
call it: Mitchell decides a step needs code -> calls `coding_implement` ->
a Hermes subprocess writes it in an isolated workdir -> Mitchell verifies the
result. Fully integrated, no manual hand-off.
"""
from __future__ import annotations

import asyncio
import json

from mitchell.coding.hermes_coder import run_hermes_code


async def coding_implement(spec: str, workdir: str | None = None) -> str:
    """Implement a coding sub-task by delegating to a Hermes-Agent subprocess.

    Returns a JSON result dict (ok, exit_code, duration, files, diff_stat,
    workdir, stdout_tail) that the caller should pass through Phase 1
    verification before trusting. Hermes writes ONLY inside the isolated
    workdir.
    """
    res = await asyncio.to_thread(run_hermes_code, spec, workdir)
    return json.dumps(res, indent=2, default=str)
