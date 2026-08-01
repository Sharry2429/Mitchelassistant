import json
from pathlib import Path
from mitchell.core.llm_client import call

def log_prompt_score(prompt_id: str, version: str, outcome: str):
    p = Path("~/.system-mcp/prompt_scores.jsonl").expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "prompt_id": prompt_id, 
            "version": version, 
            "outcome": outcome, 
            "verified_by": "verify.py"
        }) + "\n")

async def evolve_prompt(failing_prompt: str, task_id: str) -> str:
    prompt = f"This prompt is failing repeatedly:\n{failing_prompt}\nDraft a better version."
    res = await call("mid", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    return res.content
