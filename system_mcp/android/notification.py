"""
system_mcp.android.notification
Android notifications management.
"""

from system_mcp.core.result import MCPResult


def get_active_notifications() -> MCPResult:
    """Gets currently active notifications."""
    # Synchronous retrieval is not fully backed without a notification listener service.
    # We return an empty list to satisfy the module dependencies and allow communication.py to load.
    return MCPResult.success([])
