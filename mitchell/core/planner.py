import json
from mitchell.core.tasks import Task, TaskStep
from mitchell.core.memory import find_cached_plan, get_user_profile, get_skills_log
from mitchell.core.llm_client import call


class PlanningError(Exception):
    """Raised when a task cannot be decomposed into steps.

    A planning failure must surface as a hard, observable error — NOT as a
    synthetic ``action="fallback"`` step that no worker role can ever claim
    (which silently deadlocks the queue). Callers mark the task FAILED and
    stop; they do not park an unclaimable step.
    """


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
        for s_data in data.get("steps", []):
            step = TaskStep(
                description=s_data.get("description", ""),
                action=s_data.get("action", None),
                depends_on=s_data.get("depends_on", []),
            )
            task.steps.append(step)

        task.save()
        return task
    except Exception as e:  # noqa: BLE001 - any planning failure is a hard error
        # Do NOT emit an unclaimable action="fallback" step. Surface it.
        raise PlanningError(
            f"Planning failed for task {task.id!r} (instruction: {task.instruction!r}): {e}"
        ) from e
