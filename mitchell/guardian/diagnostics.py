from mitchell.core.tasks import Task

def collect_diagnostics(task_id: str) -> str:
    task = Task.load(task_id)
    if not task:
        return "Task file missing or corrupted."
        
    history = []
    for step in task.steps[-3:]:
        history.append(f"Step: {step.description}, State: {step.state}, Error: {step.error}")
        
    return "\n".join(history)
