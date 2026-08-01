import json
import os
from fuzzywuzzy import fuzz
from pathlib import Path

MEMORY_DIR = os.path.expanduser("~/.system-mcp/memory")

def get_memory_file(name: str) -> Path:
    p = Path(os.path.join(MEMORY_DIR, name))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def get_user_profile() -> str:
    p = get_memory_file("user_profile.md")
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def update_user_profile(insights: str):
    p = get_memory_file("user_profile.md")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- {insights}\n")

def get_skills_log() -> str:
    p = get_memory_file("skills_log.md")
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def log_skill(skill_name: str, purpose: str):
    p = get_memory_file("skills_log.md")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- {skill_name}: {purpose}\n")

def save_task_pattern(instruction: str, steps: list[dict]):
    p = get_memory_file("task_patterns.jsonl")
    entry = {"instruction": instruction, "steps": steps, "success_rate": 1.0}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def find_cached_plan(instruction: str, threshold: int = 85) -> list[dict] | None:
    p = get_memory_file("task_patterns.jsonl")
    if not p.exists():
        return None
        
    best_match = None
    best_score = 0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            score = fuzz.ratio(instruction.lower(), entry["instruction"].lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = entry["steps"]
                
    return best_match
