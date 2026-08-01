from mitchell.core.llm_client import call

async def research_page(url: str, goal: str, task_id: str) -> str:
    prompt = f"Goal: {goal}\nURL: {url}\nExtract relevant findings."
    res = await call("base", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    return res.content

async def synthesize_findings(findings: list[str], task_id: str) -> str:
    prompt = f"Synthesize these findings:\n" + "\n".join(findings)
    res = await call("mid", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    return res.content
