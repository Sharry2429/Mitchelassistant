"""
system_mcp.core.audit
Action logging and destructive action safety gates.
"""

from typing import Any, Dict
import time
import json
import os
from pathlib import Path

from system_mcp.core.errors import RequiresConfirmation
from system_mcp.core.config import get_config

DESTRUCTIVE = [
    "uninstall",
    "clear_data",
    "delete",
    "reboot",
    "shutdown",
    "revoke",
    "kill",
    "force-stop",
]
SENSITIVE_READ = [
    "notification.stream",
    "sms.read",
    "contacts.",
    "calendar.",
    "clipboard.read",
    "whatsapp.",
    "phone.",
    "assistant.",
    "overlay.",
]


def _get_log_path() -> Path:
    p = Path(os.path.expanduser("~/.system-mcp/audit.jsonl"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_action(
    module: str,
    action: str,
    args: Dict[str, Any],
    kwargs: Dict[str, Any],
    caller: str = "system",
):
    """Log an action to the audit file."""
    entry = {
        "timestamp": time.time(),
        "module": module,
        "action": action,
        "args": str(args),
        "kwargs": str(kwargs),
        "caller": caller,
    }
    with open(_get_log_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_destructive(action: str, confirm: bool):
    """Gate for destructive actions."""
    if get_config().safeguards:
        if action in DESTRUCTIVE and not confirm:
            raise RequiresConfirmation(
                f"Action '{action}' is destructive. Pass confirm=True to execute."
            )


def check_sensitive(module: str, action: str):
    """Gate for sensitive read actions."""
    full_action = f"{module}.{action}"
    # Just logging for now, but could be expanded to block
    log_action(module, action, {}, {}, "sensitive_check")


def get_log(since: float = 0, limit: int = 100) -> list[Dict[str, Any]]:
    """Retrieve audit logs."""
    logs = []
    p = _get_log_path()
    if not p.exists():
        return logs

    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("timestamp", 0) >= since:
                    logs.append(entry)
            except json.JSONDecodeError:
                pass

    return logs[-limit:]
