"""
scripts/real_live_demo.py — REAL end-to-end, nothing faked.

Uses the live aicredits API (AICREDITS_API_KEY + real provider keys) to drive a
REAL browser action. This is the same loop the executor uses (model ->
tool_calls -> execute real tools -> model), but scoped to real, working tools so
it's reliable and non-destructive.

REQUIRES: MITCHELL_BUDGET_CAP raised above the current logged spend
(e.g. export MITCHELL_BUDGET_CAP=100) or the budget meter will refuse the call.

Run: python scripts/real_live_demo.py "Open https://example.com and tell me the title"
"""
import asyncio
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitchell.core.llm_client import LLMResult, call  # noqa: E402
from mitchell.core.tool_provider import ToolProvider  # noqa: E402


class RealBrowserProvider(ToolProvider):
    """REAL browser execution (Playwright/Chromium). Scoped to browser tools only."""

    async def list_tools_openai(self) -> list[dict]:
        from mitchell.browser import browser as b
        out = []
        for name in ("browser_navigate", "browser_title", "browser_extract_text",
                     "browser_get_text", "browser_current_url", "browser_stop"):
            fn = getattr(b, name)
            out.append({"type": "function", "function": {
                "name": name, "description": fn.__doc__ or name,
                "parameters": {"type": "object", "properties": {}}}})
        # annotate the arg-bearing tools
        for t in out:
            if t["function"]["name"] == "browser_navigate":
                t["function"]["parameters"] = {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
            elif t["function"]["name"] == "browser_get_text":
                t["function"]["parameters"] = {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}
        return out

    async def call_tool(self, name: str, args: dict) -> str:
        from mitchell.browser import browser as b
        handler = getattr(b, name)
        res = await handler(**args)
        return str(res.data if res.ok else f"ERROR: {res.error}")


async def main(instruction: str):
    provider = RealBrowserProvider()
    tools = await provider.list_tools_openai()

    messages = [{"role": "user", "content": instruction}]
    print(f"LIVE instruction: {instruction}\n")

    final = None
    for turn in range(6):
        result: LLMResult = await call("base", messages=messages, tools=tools, task_id="live-demo")
        messages.append({"role": "assistant", "content": result.content, "tool_calls": result.tool_calls})
        if result.content:
            final = result.content
        if not result.tool_calls:
            break
        for tc in result.tool_calls:
            try:
                a = json.loads(tc.function.arguments or "{}")
            except Exception:
                a = {}
            print(f"  -> calling {tc.function.name}({json.dumps(a)})")
            out = await provider.call_tool(tc.function.name, a)
            print(f"     result: {(out or '')[:200]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": out})

    print("\n=== LIVE RESULT (model answer) ===")
    print(final or "(no text answer returned)")

    # Real spend logged by the meter
    from mitchell.core.budget import total_spend
    print(f"\n=== total real spend on disk now: ${total_spend():.4f} ===")


if __name__ == "__main__":
    instr = sys.argv[1] if len(sys.argv) > 1 else "Open https://example.com in the browser and tell me the page title and its first sentence."
    asyncio.run(main(instr))
