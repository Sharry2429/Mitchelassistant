"""
system_mcp.android.base
Shared base class for all Android modules and module-level singleton for the
CompanionBridge.
"""
from system_mcp.core.audit import check_destructive, check_sensitive
from system_mcp.core.errors import (
    ADBCommandError,
    DeviceOffline,
    RequiresConfirmation,
    SensitiveModuleDisabled,
)

# Removed companion bridge logic


def require_enabled(module: str, action: str):
    """Check that a sensitive module/action is enabled in config.

    Raises:
        SensitiveModuleDisabled – if the module is disabled.
    """
    check_sensitive(module, action)


def confirm_destructive(action: str, confirm: bool):
    """Gate a destructive action behind an explicit ``confirm=True``.

    Raises:
        RequiresConfirmation – if *confirm* is False.
    """
    check_destructive(action, confirm)
