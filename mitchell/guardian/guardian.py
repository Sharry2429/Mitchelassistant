import time
from mitchell.core.llm_client import call
from mitchell.guardian.diagnostics import collect_diagnostics

async def diagnose_and_fix(task_id: str, error_context: str = None):
    print(f"Guardian activated for task {task_id}")
    
    if task_id == "GLOBAL":
        snapshot = error_context or "No context provided."
        prompt = f"The Mitchell system has encountered a fatal crash.\nTraceback:\n{snapshot}\nPlease diagnose this error and suggest a fix."
    else:
        snapshot = collect_diagnostics(task_id)
        prompt = f"The worker is stuck or crashed on task {task_id}.\nDiagnostics:\n{snapshot}\nWhat is the likely fix?"
    
    # Mid tier first
    res = await call("mid", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    
    # Simulated escalation
    if "escalate" in res.content.lower():
        print("Escalating to top tier for diagnosis...")
        res_top = await call("top", messages=[{"role": "user", "content": prompt}], task_id=task_id)
        return res_top.content
        
    return res.content

def main():
    print("Guardian process active. Monitoring...")
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
