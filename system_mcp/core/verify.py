import os
from system_mcp.core.result import CommandResult

def verify_file_exists(path: str) -> CommandResult:
    if os.path.exists(path):
        return CommandResult(success=True, output=f"File {path} exists.")
    return CommandResult(success=False, error=f"File {path} does not exist.")

def verify_process_running(process_name: str) -> CommandResult:
    import psutil
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == process_name:
            return CommandResult(success=True, output=f"Process {process_name} is running.")
    return CommandResult(success=False, error=f"Process {process_name} is not running.")
