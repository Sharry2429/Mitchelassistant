import argparse
import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from google.antigravity.types import McpStdioServer, CustomSystemInstructions

from system_mcp.core.config import configure
from system_mcp.core.tasks import Task, TaskState
from system_mcp.core.audit import TaskScope, set_task_scope

async def run_task(instruction: str, scope: TaskScope):
    load_dotenv()
    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("Error: AICREDITS_API_KEY not found in environment.")
        sys.exit(1)
        
    # Setup unattended mode
    configure(unattended_mode=True)
    set_task_scope(scope)
    
    task = Task(id=str(uuid.uuid4()), instruction=instruction)
    task.state = TaskState.RUNNING
    task.save()
    
    # Configure AGY for tool execution
    agy_config = LocalAgentConfig(
        system_instructions=CustomSystemInstructions(
            text=f"""You are Mitchell AI, running in Autonomous Task Mode.
Your task ID is: {task.id}
Your task is: {instruction}

You must follow this lifecycle:
1. Plan your steps and write them down.
2. Execute each step using your MCP tools.
3. VERIFY every action using verification tools or reading back state.
4. If verification fails, retry.
5. Report your findings at the end.
"""
        ),
        capabilities=CapabilitiesConfig(),
        mcp_servers=[
            McpStdioServer(
                command=sys.executable,
                args=["-m", "system_mcp.mcp_server"]
            ),
            McpStdioServer(
                command="npx",
                args=["-y", "@browsermcp/mcp@0.1.3"]
            )
        ]
    )
    
    print(f"🚀 Starting autonomous task: {instruction}")
    print(f"Task ID: {task.id}")
    
    content_str = ""
    try:
        async with Agent(agy_config) as agy_agent:
            agent_response = await agy_agent.chat(instruction)
            async for token in agent_response:
                sys.stdout.write(token)
                sys.stdout.flush()
                content_str += token
            print("\n\n✅ Task execution completed.")
        task.state = TaskState.COMPLETED
    except Exception as e:
        print(f"\n\n❌ Task failed: {e}")
        task.state = TaskState.FAILED
    finally:
        import time
        task.completed_at = time.time()
        # In a full implementation, we'd parse content_str to extract steps
        task.save()

def main():
    parser = argparse.ArgumentParser(description="Mitchell Autonomous Task Runner")
    parser.add_argument("--task", type=str, required=True, help="Task instruction")
    parser.add_argument("--allow-action", type=str, action="append", default=["*"], help="Allowed actions prefix (default: *)")
    parser.add_argument("--allow-path", type=str, action="append", default=["*"], help="Allowed path globs (default: *)")
    args = parser.parse_args()
    
    # By default argparse append action doesn't override the default, it appends to it.
    # We should clean up if user provides specific arguments.
    allowed_actions = args.allow_action if args.allow_action != ["*"] else ["*"]
    allowed_paths = args.allow_path if args.allow_path != ["*"] else ["*"]
    
    if len(args.allow_action) > 1 and args.allow_action[0] == "*":
        allowed_actions = args.allow_action[1:]
    if len(args.allow_path) > 1 and args.allow_path[0] == "*":
        allowed_paths = args.allow_path[1:]
    
    scope = TaskScope(
        allowed_actions=allowed_actions,
        allowed_paths=allowed_paths
    )
    
    asyncio.run(run_task(args.task, scope))

if __name__ == "__main__":
    main()
