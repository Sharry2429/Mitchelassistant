import asyncio
import os
import sys
import time
import subprocess
import psutil
from pathlib import Path
import uuid

from mitchell.core.llm_client import call
from mitchell.core.tasks import Task, TaskState

# --- Claude Code Replica Imports ---
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

def list_jobs():
    tasks_dir = Path(os.path.expanduser("~/.system-mcp/tasks"))
    if not tasks_dir.exists():
        console.print("[dim]No active jobs.[/dim]")
        return
        
    jobs = []
    for p in tasks_dir.glob("*.json"):
        try:
            task = Task.load(p.stem)
            if task and task.state in (TaskState.PENDING, TaskState.RUNNING):
                total_steps = len(task.steps)
                completed = sum(1 for s in task.steps if s.state == TaskState.COMPLETED)
                progress = f"{completed}/{total_steps} steps" if total_steps > 0 else "Planning..."
                jobs.append(f"- **{task.id}** | `{task.state}` | {progress} | {task.instruction[:50]}...")
        except Exception:
            pass
            
    if not jobs:
        console.print("[dim]No active jobs.[/dim]")
    else:
        md = Markdown("### Active Jobs\n" + "\n".join(jobs))
        console.print(Panel(md, title="Jobs", border_style="cyan"))

def fg_job(task_id: str):
    from rich.status import Status
    try:
        last_finished_step = -1
        running_status = None
        
        while True:
            task = Task.load(task_id)
            if not task:
                console.print("[red]Task not found.[/red]")
                break
                
            # Process newly completed steps
            for i, step in enumerate(task.steps):
                if i > last_finished_step and step.state in (TaskState.COMPLETED, TaskState.FAILED):
                    if running_status:
                        running_status.stop()
                        running_status = None
                        
                    status = "[bold green]✅[/bold green]" if step.state == TaskState.COMPLETED else "[bold red]❌[/bold red]"
                    console.print(f"{status} {step.description}")
                    if step.error:
                        console.print(f"   [red]Error: {step.error}[/red]")
                    last_finished_step = i
            
            # Show spinner for current running step
            current_running = False
            for i, step in enumerate(task.steps):
                if step.state == TaskState.RUNNING and i > last_finished_step:
                    current_running = True
                    desc = f"[bold cyan]{step.description}...[/bold cyan]"
                    if running_status is None:
                        running_status = Status(desc, spinner="dots")
                        running_status.start()
                    else:
                        running_status.update(desc)
                    break
            
            if not current_running and task.state in (TaskState.PENDING, TaskState.RUNNING) and len(task.steps) == 0:
                 if running_status is None:
                     running_status = Status("[bold cyan]Planning...[/bold cyan]", spinner="dots")
                     running_status.start()
            
            if task.state in (TaskState.COMPLETED, TaskState.FAILED):
                if running_status:
                    running_status.stop()
                if task.state == TaskState.FAILED:
                    console.print(f"[bold red]Task Failed.[/bold red]")
                break
                
            time.sleep(1)
    except KeyboardInterrupt:
        if 'running_status' in locals() and running_status:
            running_status.stop()
        console.print("\n[dim]Moved to background. Type /fg to reattach.[/dim]")

async def handle_chat(message: str):
    # Lightweight heuristic to route: is this a new task?
    action_verbs = ["do", "create", "build", "run", "open", "send", "click", "tap", "type", "search", "go", "navigate", "play", "find", "read", "write", "check", "unlock", "test"]
    if len(message) > 50 or any(verb in message.lower().split() for verb in action_verbs):
        task_id = str(uuid.uuid4())
        
        # Create the task
        task = Task(id=task_id, instruction=message)
        task.state = TaskState.PENDING
        task.save()
        
        fg_job(task_id)
        return
        
    try:
        from mitchell.core.dashboard import get_windows_ip, get_android_ip
        win_ip = get_windows_ip()
        and_ip = get_android_ip()
        system_prompt = (
            "You are Mitchell, a powerful autonomous agent capable of controlling Windows and Android devices. "
            f"Current connected devices: Windows Host ({win_ip}), Android Phone ({and_ip}). "
            "Keep your answers extremely concise and contextual to the user's system."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
            res = await call("base", messages=messages)
            
        md = Markdown(res.content)
        console.print(Panel(md, title="[bold white]Mitchell[/bold white]", border_style="cyan", padding=(1, 2)))
    except Exception as e:
        console.print(f"[red]Error communicating with LLM: {e}[/red]")

async def cli_loop():
    # Deprecated: We now use the full-screen Textual UI in main()
    pass

def main():
    try:
        from mitchell.core.tui import MitchellApp
        app = MitchellApp()
        app.run()
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        console.print(f"\n[bold red]Fatal Error Detected![/bold red]")
        console.print("[yellow]Triggering Guardian Self-Healing Toolkit...[/yellow]")
        try:
            from mitchell.guardian.guardian import diagnose_and_fix
            async def run_guardian():
                res = await diagnose_and_fix("GLOBAL", error_context=error_details)
                console.print(Panel(Markdown(res), title="[bold green]Guardian Diagnosis[/bold green]", border_style="green"))
            import asyncio
            asyncio.run(run_guardian())
        except Exception as guardian_e:
            console.print(f"[bold red]Guardian also failed to diagnose the issue![/bold red]\n{guardian_e}")
            console.print("\n[dim]Original Traceback:[/dim]")
            console.print(error_details)

if __name__ == "__main__":
    main()
