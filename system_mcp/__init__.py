"""
System-MCP
Control your own devices from Python or via MCP, featuring unified Windows 
and Android automation.

Modules:
    system_mcp.windows   -- Windows automation library (Direct & MCP)
    system_mcp.android   -- Android automation library (USB-once / wireless-forever)

Import the platform you need directly:
    import system_mcp.windows as wc
    from system_mcp.windows.system import shutdown
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
