import argparse
import asyncio
import sys
import uuid
from typing import Optional

from mitchell.core.audit import TaskScope, set_task_scope
from mitchell.core.executor import execute_task
from mitchell.core.tasks import Task, TaskState, list_tasks


def ping_supervisor(task_id: str):
    # Supervisor hand-off is a later phase; the task is already persisted to the
    # queue at ~/.system-mcp/tasks/<id>.json, so any pool worker can pick it up.
    print(f"Task {task_id} queued for the worker pool.")


def main():
    parser = argparse.ArgumentParser(description="Mitchell Autonomous Task Runner")
    parser.add_argument("--task", type=str, required=True, help="Task instruction")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the task now (plan + run steps + verify) instead of only queueing it",
    )
    parser.add_argument("--allow-action", type=str, action="append", default=[], help="Allowed actions prefix")
    parser.add_argument("--allow-path", type=str, action="append", default=[], help="Allowed path globs")
    args = parser.parse_args()

    scope = TaskScope(
        allowed_actions=args.allow_action,
        allowed_paths=args.allow_path,
    )
    set_task_scope(scope)

    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction=args.task)
    task.state = TaskState.PENDING
    task.save()

    print(f"🚀 Task created: {args.task}")
    print(f"Task ID: {task.id}")

    if args.run:
        print("Executing now...")
        try:
            asyncio.run(execute_task(task_id))
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
        task = Task.load(task_id)
        print(f"Final state: {task.state if task else 'task gone'}")
        if task and task.state != TaskState.COMPLETED:
            sys.exit(2)
    else:
        ping_supervisor(task.id)


if __name__ == "__main__":
    main()
