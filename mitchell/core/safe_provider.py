"""
mitchell.core.safe_provider
===========================
A ToolProvider that wraps the real MCP tool surface but exposes only SAFE,
demonstrative tools. Read/demonstrate only: windows get/list/is, browser
nav/extract, android read/launch. Destructive, irreversible, or real-contact
actions (delete, uninstall, shutdown, send/call, clipboard writes, reg writes)
are never exposed to an autonomous executor. Safety is structural — a tool the
model can't see, it can't call.
"""
from __future__ import annotations

from mitchell.core.tool_provider import MCPToolProvider, ToolProvider


def is_safe(name: str) -> bool:
    if name.startswith("browser_"):
        return name in {"browser_navigate", "browser_title", "browser_extract_text",
                        "browser_get_text", "browser_current_url"}
    if name.startswith("core_memory_"):
        return True
    if name.startswith("coding_implement"):
        return True
    if name.startswith("windows_system_"):
        seg = name.split("_")[2:]
        head = seg[0] if seg else ""
        return head in {"get", "list", "is", "which", "uptime"} and not any(
            d in name for d in ("shutdown", "restart", "hibernate", "sleep", "lock",
                                "kill", "reg_", "powershell", "cmd", "set_", "stop_",
                                "start_", "log_off"))
    if name.startswith("windows_hardware_get_"):
        return not any(d in name for d in ("mute", "set_", "toggle", "connect", "disconnect",
                                           "add_firewall", "remove_firewall", "volume"))
    if name.startswith("windows_ui_get_"):
        return "clipboard" not in name
    if name.startswith("android_system_get_") or name.startswith("android_hardware_get_"):
        return True
    if name.startswith("android_communication_get_") or name.startswith("android_communication_open_"):
        return True
    if name.startswith("android_apps_"):
        return any(k in name for k in ("_get_", "launch", "list", "wait_for_element",
                                       "screenshot", "read"))
    return False


class SafeProvider(ToolProvider):
    """Real MCP tools filtered to the safe allowlist."""

    def __init__(self, inner: ToolProvider | None = None):
        self._inner = inner or MCPToolProvider()

    async def list_tools_openai(self):
        all_tools = await self._inner.list_tools_openai()
        return [t for t in all_tools if is_safe(t["function"]["name"])]

    async def call_tool(self, name, arguments):
        if not is_safe(name):
            return f"Error executing tool: {name} is not in the safe allowlist"
        return await self._inner.call_tool(name, arguments)
