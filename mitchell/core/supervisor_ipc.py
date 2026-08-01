import json
import time
from pathlib import Path

def get_ipc_file() -> Path:
    p = Path("~/.system-mcp/supervisor_ipc.json").expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def update_heartbeat(task_id: str, step_index: int):
    p = get_ipc_file()
    data = {"task_id": task_id, "current_step": step_index, "last_progress_ts": time.time()}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)
