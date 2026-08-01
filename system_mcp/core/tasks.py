import json
import time
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class TaskState:
    PENDING = "pending"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskStep:
    description: str
    state: str = TaskState.PENDING
    action: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    verification_passed: bool = False
    retries: int = 0
    error: Optional[str] = None
    
@dataclass
class Task:
    id: str
    instruction: str
    steps: List[TaskStep] = field(default_factory=list)
    state: str = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def get_log_path(self) -> Path:
        p = Path(os.path.expanduser(f"~/.system-mcp/tasks/{self.id}.json"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
        
    def save(self):
        with open(self.get_log_path(), "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, task_id: str) -> Optional["Task"]:
        p = Path(os.path.expanduser(f"~/.system-mcp/tasks/{task_id}.json"))
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            steps = [TaskStep(**s) for s in data.pop("steps", [])]
            return cls(**data, steps=steps)
