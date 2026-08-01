"""
system_mcp.core.audit
Action logging and destructive action safety gates.
"""

import fnmatch
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from system_mcp.core.config import get_config
from system_mcp.core.errors import RequiresConfirmation


@dataclass
class TaskScope:
    allowed_actions: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=lambda: [
        "system_mcp/core/audit.py",
        "system_mcp/core/config.py",
        "tests/*"
    ])

    def can_execute_action(self, action: str) -> bool:
        if "*" in self.allowed_actions: return True
        return any(action.startswith(prefix) for prefix in self.allowed_actions)

    def can_modify_path(self, path: str) -> bool:
        normalized_path = path.replace("\\", "/")
        # Check against protected paths first
        for prot in self.protected_paths:
            if fnmatch.fnmatch(normalized_path, prot) or fnmatch.fnmatch(normalized_path, "*/" + prot):
                return False
        
        if "*" in self.allowed_paths: return True
        for allowed in self.allowed_paths:
            if fnmatch.fnmatch(normalized_path, allowed) or fnmatch.fnmatch(normalized_path, "*/" + allowed):
                return True
        return False

DESTRUCTIVE = [
    "uninstall",
    "clear_data",
    "delete",
    "reboot",
    "shutdown",
    "revoke",
    "kill",
    "force-stop",
    "browser.",
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
    "browser.",
]

_current_task_scope: TaskScope = None

def set_task_scope(scope: TaskScope):
    global _current_task_scope
    _current_task_scope = scope


def _get_log_path() -> Path:
    p = Path(os.path.expanduser("~/.system-mcp/audit.jsonl"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_action(
    module: str,
    action: str,
    args: dict[str, Any],
    kwargs: dict[str, Any],
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
        if get_config().unattended_mode and _current_task_scope:
            if not _current_task_scope.can_execute_action(action):
                raise RequiresConfirmation(f"Action '{action}' is outside allowed TaskScope.")
            log_action("system", action, {}, {}, "destructive_check")
            return

        if action in DESTRUCTIVE and not confirm:
            raise RequiresConfirmation(
                f"Action '{action}' is destructive. Pass confirm=True to execute."
            )
        log_action("system", action, {}, {}, "destructive_check")

def check_path(path: str):
    """Gate for file/path modifications."""
    if get_config().safeguards:
        if get_config().unattended_mode and _current_task_scope:
            if not _current_task_scope.can_modify_path(path):
                raise RequiresConfirmation(f"Modifying path '{path}' is outside allowed TaskScope or is protected.")
        else:
            # Even in interactive mode, we should prevent modifying core safety files
            # unless the user has explicitly disabled safeguards.
            # We can use a default TaskScope just for path protection.
            temp_scope = TaskScope(allowed_paths=["*"]) 
            if not temp_scope.can_modify_path(path):
                raise RequiresConfirmation(f"Path '{path}' is a protected system file and cannot be modified.")


def check_sensitive(module: str, action: str, confirm: bool = False):
    """Gate for sensitive read actions."""
    if get_config().safeguards:
        full_action = f"{module}.{action}"
        if get_config().unattended_mode and _current_task_scope:
            if not _current_task_scope.can_execute_action(full_action):
                raise RequiresConfirmation(f"Action '{full_action}' is outside allowed TaskScope.")
            log_action(module, action, {}, {}, "sensitive_check")
            return

        if any(full_action.startswith(p) for p in SENSITIVE_READ) and not confirm:
            raise RequiresConfirmation(
                f"Action '{full_action}' is sensitive. Pass confirm=True to execute."
            )
    log_action(module, action, {}, {}, "sensitive_check")


def get_log(since: float = 0, limit: int = 100) -> list[dict[str, Any]]:
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
