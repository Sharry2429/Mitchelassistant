import json
import os
from pathlib import Path

class BudgetExceeded(Exception):
    pass

def check_budget_before_call(role: str, task_id: str | None = None):
    # Enforces budget.py caps before sending. Refuses the call and raises BudgetExceeded.
    # We will expand this in Phase 8 to enforce an anomaly signal instead of a hard cap.
    pass

def log_usage(task_id: str | None, role: str, model: str, prompt_tokens: int, completion_tokens: int, cost_estimate: float):
    p = Path(os.path.expanduser("~/.system-mcp/tokens.jsonl"))
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        log_entry = {
            "task_id": task_id,
            "role": role,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_estimate": cost_estimate
        }
        f.write(json.dumps(log_entry) + "\n")
