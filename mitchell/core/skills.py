import os
import importlib.util
from pathlib import Path
from mitchell.core.llm_client import call

SKILLS_DIR = Path("~/.system-mcp/skills").expanduser()

def discover_skills():
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for p in SKILLS_DIR.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists() and (p / "tool.py").exists():
            skills.append(p.name)
    return skills

def hot_load_skill(skill_name: str):
    skill_path = SKILLS_DIR / skill_name / "tool.py"
    if not skill_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"skills.{skill_name}", str(skill_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

async def draft_skill(need_description: str, task_id: str | None = None) -> str:
    prompt = f"Draft a skill for: {need_description}. Provide SKILL.md, tool.py, test_tool.py."
    res = await call("mid", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    return res.content

async def review_skill(skill_code: str, task_id: str | None = None) -> bool:
    prompt = f"Review this skill code. Does it do anything outside its stated purpose or destructive? Answer YES if safe, NO if unsafe.\n\nCode:\n{skill_code}"
    res = await call("top", messages=[{"role": "user", "content": prompt}], task_id=task_id)
    return "YES" in res.content.upper()
