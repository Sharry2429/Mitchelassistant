"""
mitchell.coding.hermes_gateway
==============================
Give Mitchell "all the tools Hermes has."

Hermes' full toolset (web, browser, terminal, file, code_execution, vision,
image_gen, tts, memory, skills, todo, cron, delegation, computer_use, ...) is
exposed to Mitchell as named, callable tools. Each delegates to a real
`hermes chat -q` subprocess constrained to that toolset (`-t TOOLSET`), and
returns the agent's ground-truth output. These are real executions — not stubs
— and each call is a fresh, isolated Hermes session.

MANIFEST mirrors `hermes tools list` for the enabled built-in toolsets.
"""
from __future__ import annotations

import subprocess
import time

# name -> (toolset flag, human description) for EVERY enabled Hermes toolset
MANIFEST = [
    ("hermes_web",          "web",          "Web Search & Scraping"),
    ("hermes_browser",      "browser",      "Browser Automation"),
    ("hermes_terminal",     "terminal",     "Terminal & Processes"),
    ("hermes_file",         "file",         "File Operations"),
    ("hermes_code",         "code_execution","Code Execution"),
    ("hermes_vision",       "vision",       "Vision / Image Analysis"),
    ("hermes_image",        "image_gen",    "Image Generation"),
    ("hermes_tts",          "tts",          "Text-to-Speech"),
    ("hermes_memory",       "memory",       "Persistent Memory"),
    ("hermes_skills",       "skills",       "Skills"),
    ("hermes_todo",         "todo",         "Task Planning"),
    ("hermes_cron",         "cronjob",      "Cron Jobs"),
    ("hermes_delegate",     "delegation",   "Task Delegation"),
    ("hermes_computer",     "computer_use", "Computer Use / GUI"),
]

# The union toolset gives full Hermes capability in one call.
UNION = ",".join(s for _, s, _ in MANIFEST)


def _run(prompt: str, toolset: str, timeout: int = 900) -> str:
    argv = ["hermes", "--yolo", "-t", toolset, "chat", "-q", prompt]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"ERROR: hermes ({toolset}) timed out after {timeout}s"
    out = (proc.stdout or "").strip()
    tail = out[-1500:] or (proc.stderr or "")[-1500:]
    err = f"\n[exit {proc.returncode}]"
    return (tail + err) if proc.returncode != 0 else tail


def hermes_agent(prompt: str, timeout: int = 900) -> str:
    """Full Hermes toolset — every Hermes capability in one call."""
    return _run(prompt, UNION, timeout)


def hermes_web(query: str, timeout: int = 300) -> str:
    return _run(f"Use web search to answer: {query}", "web", timeout)


def hermes_terminal(cmd: str, timeout: int = 300) -> str:
    return _run(f"Run this terminal command and report its output: {cmd}", "terminal", timeout)


def hermes_file(task: str, timeout: int = 600) -> str:
    return _run(task, "file", timeout)


def hermes_browser(task: str, timeout: int = 600) -> str:
    return _run(task, "browser", timeout)


def hermes_vision(question: str, image_path: str = "", timeout: int = 300) -> str:
    prompt = f"Analyze the image '{image_path}' and answer: {question}" if image_path else question
    return _run(prompt, "vision", timeout)


def hermes_memory(task: str, timeout: int = 300) -> str:
    return _run(task, "memory", timeout)


def hermes_skills(task: str, timeout: int = 300) -> str:
    return _run(task, "skills", timeout)
