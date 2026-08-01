import os

from mitchell.core.result import MCPResult


def verify_file_exists(path: str) -> MCPResult:
    if os.path.exists(path):
        return MCPResult.success(output=f"File {path} exists.")
    return MCPResult.fail(error=f"File {path} does not exist.")

def verify_process_running(process_name: str) -> MCPResult:
    import psutil
    for p in psutil.process_iter(['name']):
        if p.info['name'] == process_name:
            return MCPResult.success(output=f"Process {process_name} is running.")
    return MCPResult.fail(error=f"Process {process_name} is not running.")
