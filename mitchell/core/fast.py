"""
mitchell.core.fast
==================
Lightning-fast task execution.

The full plan->executor->verify loop (Phase 2) is correct but slow for simple
tasks (multiple LLM round-trips -> tens of seconds). ``fast_do`` runs a lean
single-thread agent loop -- no separate planning pass, no per-step verification
overhead -- starting straight from the instruction and letting the model call
tools until it has the answer. Usually only a few LLM round-trips.

Unattended-friendly: no prompts, no confirmations, safe-tool-scoped by default.
Complex tasks still go through the full verified loop (mitchell.core.do falls
back to it when the fast path can't produce an answer).
"""
from __future__ import annotations

import json
import time

from mitchell.core.llm_client import call
from mitchell.core.tool_provider import ToolProvider

MAX_TURNS = 5


async def fast_do(instruction: str, tools: ToolProvider, tier: str = "base", llm_call=None) -> dict:
    """Execute a task via a lean agent loop. Returns {answer, tool, turns, elapsed}."""
    t0 = time.monotonic()
    inject = llm_call or call
    openai_tools = await tools.list_tools_openai()

    messages = [{"role": "user", "content": instruction}]
    last_tool = None
    final = None
    turns = 0

    for turns in range(1, MAX_TURNS + 1):
        result = await inject(tier, messages=messages, tools=openai_tools, task_id="fast")

        # Sanitize tool results so we never echo raw MCP envelopes into answers.
        content = (result.content or "").strip()
        if _looks_like_envelope(content):
            content = ""
        if content:
            final = content

        if not result.tool_calls:
            break

        messages.append({"role": "assistant", "content": result.content or "", "tool_calls": result.tool_calls})
        for tcall in result.tool_calls:
            name = tcall.function.name
            try:
                args = json.loads(tcall.function.arguments or "{}")
            except Exception:  # noqa: BLE001
                args = {}
            tool_result = await tools.call_tool(name, args)
            last_tool = name
            messages.append({"role": "tool", "tool_call_id": tcall.id, "name": name, "content": tool_result})

    answer = final or last_tool or ""
    return {"answer": answer, "tool": last_tool, "turns": turns,
            "elapsed": round(time.monotonic() - t0, 2)}


def _looks_like_envelope(text: str) -> bool:
    """Detect raw MCP/TextContent envelopes so we don't present them as answers."""
    return text.startswith("[TextContent(") or text.startswith("content=[TextContent(") or text.startswith('{"ok":')
