"""
mitchell.mcp_server
Unified MCP Server exposing both Windows and Android modules under a single namespace.
"""

import importlib
import inspect

from fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("System-MCP")


def register_platform_tools(platform: str, module_names: list[str]):
    for mod_name in module_names:
        try:
            mod = importlib.import_module(f"mitchell.{platform}.{mod_name}")
            for name, func in inspect.getmembers(mod, inspect.isfunction):
                if not name.startswith("_"):
                    # Prefix the tool name with the platform and module for a unified namespace
                    tool_name = f"{platform}_{mod_name}_{name}"
                    func.__name__ = tool_name
                    # FastMCP tool registration
                    try:
                        mcp.add_tool(func)
                    except (ValueError, TypeError, Exception) as e:
                        print(f"Skipping tool {tool_name}: {e}")
        except ImportError as e:
            print(f"ImportError loading {platform}.{mod_name}: {e}")


# Windows Modules
windows_modules = ["system", "hardware", "ui", "apps", "tts", "stt"]

# Android Modules
android_modules = ["system", "hardware", "interaction", "apps", "communication"]

# Core Modules
core_modules = ["memory", "verify", "tasks"]

register_platform_tools("windows", windows_modules)
register_platform_tools("android", android_modules)
register_platform_tools("core", core_modules)

# Browser module — functions are already named browser_*, so register them
# with their natural names (no platform/module re-prefix) and skip imports.
def _register_browser_tools():
    bm = importlib.import_module("mitchell.browser.browser")
    for name, func in inspect.getmembers(bm, inspect.isfunction):
        if name.startswith("browser_") and not name.startswith("_"):
            try:
                mcp.add_tool(func)
            except Exception as e:  # noqa: BLE001
                print(f"Skipping browser tool {name}: {e}")
_register_browser_tools()


# Coding module — Hermes-Agent subprocess worker, registered with a clean name.
def _register_coding_tools():
    cm = importlib.import_module("mitchell.coding.mcp_tools")
    mcp.add_tool(cm.coding_implement)
_register_coding_tools()


# Tool Foundry — previously drafted & verified tools become callable MCP tools.
def _register_foundry_tools():
    try:
        from mitchell.core.tool_registry import list_registered, load_foundry_function
        for name in list_registered():
            fn = load_foundry_function(name)
            if fn is not None:
                mcp.add_tool(fn)
    except Exception:  # noqa: BLE001 - foundry may be empty/absent
        pass
_register_foundry_tools()


# Hermes tool gateway — expose "all the tools Hermes has" to Mitchell.
def _register_hermes_tools():
    hg = importlib.import_module("mitchell.coding.hermes_gateway")
    for tool_name, _flag, _desc in hg.MANIFEST:
        fn = getattr(hg, tool_name, None)
        if fn is not None:
            try:
                mcp.add_tool(fn)
            except Exception as e:  # noqa: BLE001
                print(f"Skipping hermes tool {tool_name}: {e}")
    mcp.add_tool(hg.hermes_agent)
_register_hermes_tools()


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
