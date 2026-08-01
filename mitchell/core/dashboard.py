import os
import subprocess
import time
import json
from pathlib import Path
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box

def get_windows_ip() -> str:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "[red]Offline / Error[/red]"

def get_android_ip() -> str:
    try:
        result = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=2)
        for line in result.stdout.splitlines():
            if " android " in line:
                parts = line.split()
                if parts:
                    return parts[0]
    except Exception:
        pass
    return "[yellow]Disconnected[/yellow]"

def generate_device_table() -> Table:
    table = Table(box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Device / Node", style="cyan")
    table.add_column("Tailscale IP", style="green")
    table.add_column("Status")
    
    win_ip = get_windows_ip()
    win_status = "[green]Online[/green]" if "Offline" not in win_ip else "[red]Offline[/red]"
    table.add_row("💻 Windows (Host)", win_ip, win_status)
    
    and_ip = get_android_ip()
    if "Disconnected" in and_ip:
        and_status = "[yellow]Disconnected[/yellow]"
    elif "Offline" in and_ip:
        and_status = "[red]Offline[/red]"
    else:
        and_status = "[green]Online[/green]"
    table.add_row("📱 Android (ADB)", and_ip, and_status)
    
    return table

def generate_task_table() -> Table:
    table = Table(box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Task ID", style="magenta", width=36)
    table.add_column("State", width=12)
    table.add_column("Progress", width=10)
    table.add_column("Instruction", style="white")
    table.add_column("Worker", style="dim")
    
    tasks_dir = Path(os.path.expanduser("~/.system-mcp/tasks"))
    if not tasks_dir.exists():
        table.add_row("N/A", "N/A", "N/A", "No tasks directory found.", "")
        return table
        
    tasks_list = []
    for p in tasks_dir.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = data.get("state", "UNKNOWN")
            tasks_list.append(data)
        except Exception:
            pass
            
    # Sort by creation / recent if possible, or just ID
    tasks_list.sort(key=lambda x: x.get("id", ""), reverse=True)
    
    if not tasks_list:
        table.add_row("None", "-", "-", "No active or completed tasks.", "")
    else:
        for t in tasks_list:
            state = t.get("state", "UNKNOWN")
            color = "yellow" if state in ("PENDING", "RUNNING") else ("green" if state == "COMPLETED" else "red")
            
            steps = t.get("steps", [])
            total = len(steps)
            completed = sum(1 for s in steps if s.get("state") == "COMPLETED")
            progress = f"{completed}/{total}" if total > 0 else "Plan..."
            
            instruction = t.get("instruction", "")
            if len(instruction) > 50:
                instruction = instruction[:47] + "..."
                
            # Find which worker claimed the last running step
            worker = ""
            for s in reversed(steps):
                if s.get("claimed_by"):
                    worker = s["claimed_by"]
                    break
                    
            table.add_row(
                t.get("id", "Unknown"),
                f"[{color}]{state}[/{color}]",
                progress,
                instruction,
                worker
            )
            
    return table

def generate_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="devices", size=7),
        Layout(name="tasks")
    )
    
    layout["header"].update(Panel("[bold cyan]Mitchell Autonomous Agent - Command Center[/bold cyan]", border_style="cyan"))
    layout["devices"].update(Panel(generate_device_table(), title="Network & Devices", border_style="green"))
    layout["tasks"].update(Panel(generate_task_table(), title="Background Task Pool", border_style="magenta"))
    
    return layout

def main():
    try:
        with Live(generate_layout(), refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(1)
                live.update(generate_layout())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
