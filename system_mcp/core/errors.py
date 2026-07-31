"""
system_mcp.core.errors
Unified error taxonomy for System-MCP (Android & Windows).
"""


class SystemMCPError(Exception):
    """Base exception for all System-MCP errors."""


class ADBCommandError(SystemMCPError):
    """Raised when an ADB command fails."""


class RoleDialerRequired(SystemMCPError):
    """Raised when an operation requires Mitchell AI to be the default dialer."""


class PermissionDenied(SystemMCPError):
    """Raised when an operation is blocked by OS permissions (e.g. unrooted device)."""


class DeviceOffline(SystemMCPError):
    """Raised when the device is not reachable (USB disconnected / Wireless dropped)."""


class RequiresConfirmation(SystemMCPError):
    """Raised when a destructive action is attempted without confirm=True."""


class SensitiveModuleDisabled(SystemMCPError):
    """Raised when a sensitive module is accessed but not enabled in config."""


class OsHardLimit(SystemMCPError):
    """Raised when the OS definitively blocks an action (e.g., iOS/Android sandbox)."""


class TimeoutError(SystemMCPError):
    """Raised when a wait_for_element or network call times out."""


class InvalidSelectorError(SystemMCPError):
    """Raised when an invalid UI element selector is provided."""
