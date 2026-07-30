"""
system_mcp.core.errors
Unified error taxonomy for System-MCP (Android & Windows).
"""

class SystemMCPError(Exception):
    """Base exception for all System-MCP errors."""
    pass

class RoleDialerRequired(SystemMCPError):
    """Raised when an operation requires Mitchell AI to be the default dialer."""
    pass

class PermissionDenied(SystemMCPError):
    """Raised when an operation is blocked by OS permissions (e.g. unrooted device)."""
    pass

class RequiresCompanionApp(SystemMCPError):
    """Raised when a feature needs the Companion APK but it isn't installed/active."""
    pass

class RequiresCompanionUpdate(SystemMCPError):
    """Raised when the Companion APK version doesn't match the Python library."""
    pass

class DeviceOffline(SystemMCPError):
    """Raised when the device is not reachable (USB disconnected / Wireless dropped)."""
    pass

class RequiresConfirmation(SystemMCPError):
    """Raised when a destructive action is attempted without confirm=True."""
    pass

class SensitiveModuleDisabled(SystemMCPError):
    """Raised when a sensitive module is accessed but not enabled in config."""
    pass

class OsHardLimit(SystemMCPError):
    """Raised when the OS definitively blocks an action (e.g., iOS/Android sandbox)."""
    pass

class TimeoutError(SystemMCPError):
    """Raised when a wait_for_element or network call times out."""
    pass

class InvalidSelectorError(SystemMCPError):
    """Raised when an invalid UI element selector is provided."""
    pass
