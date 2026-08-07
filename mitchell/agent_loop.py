import argparse
import asyncio
import sys
import uuid

from mitchell.core import config as config_module


def main():
    parser = argparse.ArgumentParser(description="Mitchell worker process")
    parser.add_argument(
        "--role",
        default="worker-general",
        help="Worker role: worker-general | worker-coder | worker-operator | worker-research",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Specific task id to run (omit to serve the task queue as a pool worker)",
    )
    args = parser.parse_args()

    from mitchell.core.executor import worker_loop  # decoupled: no MCP server import

    config_module.configure(unattended_mode=True)

    worker_id = f"{args.role}-{uuid.uuid4().hex[:8]}"
    print(f"🚀 Starting {args.role} ({worker_id})" + (f" -> task {args.task}" if args.task else " (queue mode)"))

    try:
        asyncio.run(worker_loop(worker_id, args.role, task_id=args.task))
    except KeyboardInterrupt:
        print(f"\n🛑 {worker_id} shutting down cleanly.")


if __name__ == "__main__":
    main()
