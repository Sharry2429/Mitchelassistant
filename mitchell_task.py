import argparse
import sys
import uuid
from typing import Optional

from mitchell.core.audit import TaskScope, set_task_scope
from mitchell.core.tasks import Task, TaskState

def ping_supervisor(task_id: str):
    # This will be implemented in supervisor_ipc in a later phase.
    print(f"Task {task_id} queued for the worker pool.")

def main():
    parser = argparse.ArgumentParser(description="Mitchell Autonomous Task Runner")
    parser.add_argument("--task", type=str, required=True, help="Task instruction")
    parser.add_argument("--allow-action", type=str, action="append", default=[], help="Allowed actions prefix")
    parser.add_argument("--allow-path", type=str, action="append", default=[], help="Allowed path globs")
    args = parser.parse_args()

    scope = TaskScope(
        allowed_actions=args.allow_action,
        allowed_paths=args.allow_path
    )
    
    # In full implementation, scope might be stored inside task or elsewhere, 
    # but for now we follow the thin client model.
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction=args.task)
    task.state = TaskState.PENDING
    task.save()
    
    print(f"🚀 Task created: {args.task}")
    print(f"Task ID: {task.id}")
    ping_supervisor(task.id)

if __name__ == "__main__":
    main()
