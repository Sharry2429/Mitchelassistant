"""
system_mcp.android.base
Shared base class for all Android modules and module-level singleton for the
CompanionBridge.
"""
from system_mcp.core.audit import check_destructive, check_sensitive
from system_mcp.core.errors import (
    RequiresCompanionApp,
    RequiresConfirmation,
    SensitiveModuleDisabled,
)

# ------------------------------------------------------------------ #
# Companion Bridge singleton
# ------------------------------------------------------------------ #

_bridge_instance = None


def get_companion_bridge():
    """Return the shared CompanionBridge singleton.

    Creates the instance on first call.  Every module that needs the
    companion MUST call this instead of instantiating its own bridge.

    Raises:
        RequiresCompanionApp – if the bridge cannot connect.
    """
    global _bridge_instance
    if _bridge_instance is None:
        from system_mcp.android.bridge import CompanionBridge
        _bridge_instance = CompanionBridge()
    return _bridge_instance


def reset_companion_bridge():
    """Close and discard the singleton (used after reconnect)."""
    global _bridge_instance
    if _bridge_instance is not None:
        try:
            _bridge_instance.close()
        except Exception:
            pass
        _bridge_instance = None


# ------------------------------------------------------------------ #
# Shared one-liner helpers
# ------------------------------------------------------------------ #

def require_companion():
    """Ensure the Companion APK bridge is available.

    Returns the bridge instance on success.

    Raises:
        RequiresCompanionApp – if the bridge cannot connect.
    """
    return get_companion_bridge()


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
