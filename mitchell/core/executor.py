import time
import json
import asyncio
from mitchell.core.tasks import Task, TaskState, TaskStep
from mitchell.core.agent_pool import claim_next_step, mark_step_completed, mark_step_failed, DeviceLock
from mitchell.core.llm_client import call
import mitchell.core.verify as verify_module

from mitchell.mcp_server import mcp

async def get_openai_tools():
    tools = await mcp.list_tools()
    openai_tools = []
    for t in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.parameters or {}
            }
        })
    return openai_tools

async def run_step(task_id: str, step: TaskStep, worker_role: str) -> bool:
    # Automatically ensure Android is unlocked if applicable
    if step.action and "android" in step.action.lower() or worker_role == "worker-operator":
        try:
            from mitchell.android.system import unlock_device
            unlock_device()
        except Exception as e:
            print(f"Auto-unlock failed silently: {e}")
            
    tier = "base"
    retries = 0
    max_retries = 2
    
    openai_tools = await get_openai_tools()
    
    while retries <= max_retries:
        if retries == 2:
            tier = "mid"
            
        prompt = f"Execute step: {step.description}\nNeeded action namespace: {step.action}\nPrevious error (if any): {step.error}"
        messages = [{"role": "user", "content": prompt}]
        
        max_turns = 10
        turn = 0
        
        while turn < max_turns:
            if worker_role == "worker-operator":
                with DeviceLock():
                    result = await call(tier, messages=messages, tools=openai_tools, task_id=task_id)
            else:
                result = await call(tier, messages=messages, tools=openai_tools, task_id=task_id)
                
            messages.append({
                "role": "assistant",
                "content": result.content,
                "tool_calls": result.tool_calls
            })
            
            if not result.tool_calls:
                break
                
            for tcall in result.tool_calls:
                tool_name = tcall.function.name
                try:
                    args = json.loads(tcall.function.arguments)
                except Exception:
                    args = {}
                    
                tool_res_str = ""
                try:
                    resp = await mcp.call_tool(tool_name, arguments=args)
                    texts = [c.text for c in resp if hasattr(c, 'text')]
                    tool_res_str = "\n".join(texts) if texts else str(resp)
                except Exception as e:
                    tool_res_str = f"Error executing tool: {e}"
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tcall.id,
                    "name": tool_name,
                    "content": tool_res_str
                })
            
            turn += 1

        if hasattr(verify_module, "verify_step"):
            verified = verify_module.verify_step(step, messages)
        else:
            verified = True
            
        if verified:
            return True
            
        retries += 1
        step.error = f"Verification failed on attempt {retries}"
        
    return False

async def worker_loop(worker_id: str, worker_role: str):
    while True:
        task_id = "test-task" 
        
        step_idx, step = claim_next_step(task_id, worker_id, worker_role)
        if step:
            success = await run_step(task_id, step, worker_role)
            if success:
                mark_step_completed(task_id, step_idx)
            else:
                mark_step_failed(task_id, step_idx, step.error or "Failed after retries")
        else:
            await asyncio.sleep(1)
