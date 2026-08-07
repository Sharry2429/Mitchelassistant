"""
scripts/run_autonomous.py — put the COMPLETE load on Mitchell.

Mitchell (its own agent loop) plans, executes, verifies, and logs every task
using REAL live tools + REAL aicredits LLM calls. This driver only:
  * launches each task via execute_task (real planner + real executor + real
    MCP tools + real Phase-1 verification),
  * scope the toolbox to SAFE/demonstrative tools (no destructive actions),
  * captures wall-clock timing per task.

Run: python scripts/run_autonomous.py
Requires AICREDITS_API_KEY + MITCHELL_BUDGET_CAP above current spend.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitchell.core.executor import execute_task  # noqa: E402
from mitchell.core.tool_provider import MCPToolProvider, ToolProvider  # noqa: E402


# ---- SAFE allowlist: read/demonstrate only, no destructive/irreversible tools ----
def _is_safe(name: str) -> bool:
    if name.startswith("browser_"):
        return name in {"browser_navigate", "browser_title", "browser_extract_text",
                        "browser_get_text", "browser_current_url"}
    if name.startswith("core_memory_"):
        return True
    if name.startswith("windows_system_"):
        seg = name.split("_")[2:]
        head = seg[0] if seg else ""
        return head in {"get", "list", "is", "which", "get_uptime"} and not any(
            d in name for d in ("shutdown", "restart", "hibernate", "sleep", "lock",
                                "kill", "reg_", "powershell", "cmd", "set_", "stop_",
                                "start_", "log_off", "restart_service"))
    if name.startswith("windows_hardware_get_"):
        # read-only hardware reads only (exclude muting/volume/firewall/connect)
        return not any(d in name for d in ("mute", "set_", "toggle", "connect", "disconnect",
                                           "add_firewall", "remove_firewall", "volume"))
    if name.startswith("windows_ui_get_"):
        return "clipboard" not in name  # allow window/cursor reads, not clipboard writes
    if name.startswith("android_system_get_") or name.startswith("android_hardware_get_"):
        return True
    if name.startswith("android_communication_get_") or name.startswith("android_communication_open_"):
        return True  # read notifications/chats/call-history / open dialer (no send/call)
    if name.startswith("android_apps_"):
        return any(k in name for k in ("_get_", "launch", "list", "wait_for_element",
                                       "screenshot", "read"))
    return False


class ScopedRealProvider(ToolProvider):
    """Real MCP tools, filtered to the safe allowlist."""

    def __init__(self, inner: MCPToolProvider):
        self._inner = inner

    async def list_tools_openai(self):
        all_tools = await self._inner.list_tools_openai()
        return [t for t in all_tools if _is_safe(t["function"]["name"])]

    async def call_tool(self, name, arguments):
        return await self._inner.call_tool(name, arguments)


TASKS = [
    "On the Android phone (device model CPH2707, Android 16), read the current battery level and charging status, then report the phone model and Android version.",
    "On the Android phone, open the Calculator app, wait for it to load, and then report the name of the app that is currently in the foreground.",
    "Open https://example.com in the browser and report the page title and the first sentence of the page.",
    "Get basic info about this Windows PC: OS version, CPU model, total memory, and list the top 5 processes by CPU usage.",
]


async def one(instruction: str, idx: int):
    from mitchell.core.tasks import Task, TaskState
    provider = ScopedRealProvider(MCPToolProvider())
    tools = await provider.list_tools_openai()
    shown = [t["function"]["name"] for t in tools]
    print(f"\n{'='*64}\nTASK {idx}: {instruction}\n  exposed safe tools: {len(shown)} "
          f"({', '.join(shown[:6])} ...)\n{'='*64}")
    # Mitchell needs a persisted task to load; create it like mitchell-task does.
    tout = Task(id=f"auto-{idx}", instruction=instruction)
    tout.state = TaskState.PENDING
    tout.save()
    t0 = time.monotonic()
    result = await execute_task(tout.id, tools=provider)
    dt = time.monotonic() - t0

    from mitchell.core.tasks import Task
    from mitchell.core import memory
    task = Task.load(f"auto-{idx}")
    summary = {}
    if task:
        summary = {"state": task.state, "steps": len(task.steps),
                   "completed": sum(1 for s in task.steps if s.state == "completed"),
                   "failed": sum(1 for s in task.steps if s.state == "failed")}
    eps = [e for e in memory.list_episodes() if e["task_id"] == f"auto-{idx}"]
    return {
        "idx": idx, "instruction": instruction, "elapsed_sec": round(dt, 2), **summary,
        "episodes": len(eps), "result": result,
    }


async def main():
    print(f"Budget cap: ${os.environ.get('MITCHELL_BUDGET_CAP','?')}")
    print(f"ANDROID_SERIAL: {os.environ.get('ANDROID_SERIAL','?')}")
    rows = []
    t_total0 = time.monotonic()
    for i, task in enumerate(TASKS, 1):
        try:
            rows.append(await one(task, i))
        except Exception as e:  # noqa: BLE001
            print(f"\n[TASK {i} ERROR] {type(e).__name__}: {e}")
            rows.append({"idx": i, "instruction": task, "elapsed_sec": -1, "error": str(e)})
    total = round(time.monotonic() - t_total0, 2)

    print(f"\n{'='*64}\nTIMING REPORT (Mitchell autonomous, real API)\n{'='*64}")
    for r in rows:
        state = r.get("state", "ERR")
        steps = r.get("steps", "-")
        comp = r.get("completed", "-")
        fail = r.get("failed", "-")
        print(f"  Task {r['idx']}: {r['elapsed_sec']:>6.2f}s | state={state} "
              f"| steps={steps} (ok={comp} fail={fail}) | episodes={r.get('episodes','-')}")
    print(f"\n  TOTAL wall-clock: {total:.2f}s across {len(rows)} tasks\n")


if __name__ == "__main__":
    asyncio.run(main())
