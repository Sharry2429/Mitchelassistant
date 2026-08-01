import json
from mitchell.core.tasks import Task, TaskStep
from mitchell.core.memory import find_cached_plan, get_user_profile, get_skills_log
from mitchell.core.llm_client import call

async def create_plan(task: Task) -> Task:
    # Check cache first
    cached_steps = find_cached_plan(task.instruction)
    if cached_steps:
        # Reconstruct TaskStep objects
        task.steps = [TaskStep(**s) for s in cached_steps]
        task.save()
        return task

    # No cache hit, call LLM
    profile = get_user_profile()
    skills = get_skills_log()
    
    prompt = f"""You are a planner for Mitchell Autonomous Agent.
Break down the following instruction into sequential steps.
Available tool namespaces: 'android.*', 'windows.system', 'windows.ui', 'vision', 'browser', 'skills.*', 'research.*'

Instruction: {task.instruction}

User Profile Context:
{profile}

Available Custom Skills:
{skills}

Output a JSON object with a 'steps' array.
Each step should have 'description', 'action' (the tool namespace needed), and optional 'depends_on' (list of 0-indexed step indices this step depends on).
"""
    messages = [{"role": "user", "content": prompt}]
    
    # We use 'base' tier as requested
    result = await call("base", messages=messages, task_id=task.id)
    
    # Parse output, expecting JSON block.
    try:
        content = result.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        data = json.loads(content)
        
        task.steps = []
        for i, s_data in enumerate(data.get("steps", [])):
            step = TaskStep(
                description=s_data.get("description", ""),
                action=s_data.get("action", None),
                depends_on=s_data.get("depends_on", [])
            )
            task.steps.append(step)
            
        task.save()
    except Exception as e:
        # Fallback if planning fails
        task.steps = [TaskStep(description=task.instruction, action="fallback")]
        task.save()
        
    return task
