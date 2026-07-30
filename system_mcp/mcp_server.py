"""
system_mcp.mcp_server
Unified MCP Server exposing both Windows and Android modules under a single namespace.
"""
from fastmcp import FastMCP
import importlib
import inspect

from system_mcp.core.config import get_config

# Initialize MCP Server
mcp = FastMCP("System-MCP")

def register_platform_tools(platform: str, module_names: list[str]):
    for mod_name in module_names:
        try:
            mod = importlib.import_module(f"system_mcp.{platform}.{mod_name}")
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
windows_modules = [
    "system", "hardware", "ui", "apps"
]

# Android Modules
android_modules = [
    "system", "hardware", "interaction", "apps", "communication"
]

register_platform_tools("windows", windows_modules)
register_platform_tools("android", android_modules)

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
