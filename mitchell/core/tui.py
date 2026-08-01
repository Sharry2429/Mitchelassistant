import asyncio
import os
import psutil
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal
from textual.widgets import Static, Input, RichLog, Select
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box

from mitchell.core.dashboard import get_windows_ip, get_android_ip, generate_device_table, generate_task_table

class StatsWidget(Static):
    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_stats)

    def update_stats(self) -> None:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.update(f"💻 CPU: {cpu}%   |   🧠 RAM: {mem}%   |   🔋 Agents Active: Auto-Scaling   |   🌐 Network: Secure")

class DeviceWidget(Static):
    def on_mount(self) -> None:
        self.set_interval(2.0, self.update_devices)
        self.update_devices()
        
    def update_devices(self) -> None:
        self.update(Panel(generate_device_table(), title="Network Nodes", border_style="green", padding=(0,0)))

class ActivityLogWidget(Static):
    def on_mount(self) -> None:
        self.set_interval(1.5, self.update_processes)
        self.update_processes()
        
    def update_processes(self) -> None:
        table = Table(box=box.SIMPLE_HEAD, expand=True)
        table.add_column("PID", style="cyan")
        table.add_column("Process", style="white")
        table.add_column("CPU%", justify="right", style="green")
        table.add_column("RAM%", justify="right", style="magenta")
        
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if p.info['name'] and p.info['name'] not in ('System Idle Process', 'System'):
                    procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        
        for p in procs[:8]:
            cpu = f"{p.get('cpu_percent', 0.0):.1f}"
            ram = f"{p.get('memory_percent', 0.0):.1f}"
            name = p.get('name', 'Unknown')
            if len(name) > 15:
                name = name[:12] + "..."
            table.add_row(str(p.get('pid')), name, cpu, ram)
            
        self.update(Panel(table, title="Live System Reality", border_style="magenta", padding=(0,0)))

class MitchellApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: 3 1fr 3;
        grid-columns: 1fr 2fr 1fr;
    }
    
    #stats {
        column-span: 3;
        height: 3;
        content-align: center middle;
        background: $panel;
        color: cyan;
        text-style: bold;
    }
    
    #devices {
        height: 100%;
        padding: 0 1;
    }
    
    #activity_log {
        height: 100%;
        padding: 0 1;
    }
    
    #chat_log {
        height: 100%;
        border: round cyan;
        background: $surface;
        padding: 0 1;
    }
    
    #input_container {
        column-span: 3;
        height: 3;
        dock: bottom;
    }
    
    #model_select {
        width: 25;
        height: 3;
    }
    
    #input_area {
        width: 1fr;
        height: 3;
        background: $boost;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatsWidget(id="stats")
        yield DeviceWidget(id="devices")
        
        self.chat_log = RichLog(id="chat_log", highlight=True, markup=True)
        yield self.chat_log
        
        yield ActivityLogWidget(id="activity_log")
        
        with Horizontal(id="input_container"):
            yield Select(
                [
                    ("Luna (Base)", "base"),
                    ("Terra (Mid)", "mid"),
                    ("Sol (Top)", "top"),
                    ("Seed Flash", "seed"),
                    ("DeepSeek Flash", "deepseek"),
                    ("Gemini Flash", "gemini"),
                ],
                value="gemini",
                id="model_select",
                allow_blank=False
            )
            yield Input(placeholder="COMMAND CENTER READY > Type an instruction or question...", id="input_area")

    def on_mount(self) -> None:
        self.chat_log.write("[bold cyan]Mitchell Systems Online.[/bold cyan]")
        self.chat_log.write("[dim]Awaiting command...[/dim]")
        self.run_startup_tasks()
        
    from textual import work
    
    @work
    async def run_startup_tasks(self) -> None:
        try:
            from mitchell.core.adb_setup import setup_wireless_adb
            setup_wireless_adb()
            self.chat_log.write("[dim green]ADB Network Interface Connected.[/dim green]")
        except Exception as e:
            self.chat_log.write(f"[dim red]ADB Setup Failed: {e}[/dim red]")

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        val = message.value.strip()
        if not val:
            return
            
        message.input.value = ""
        self.chat_log.write(f"\n[bold green]You:[/bold green] {val}")
        self.process_chat(val)

    from textual import work

    @work
    async def process_chat(self, val: str) -> None:
        self.chat_log.write("[dim]Thinking...[/dim]")
        try:
            from mitchell.core.llm_client import call
            from mitchell.mcp_server import mcp
            import json

            win_ip = get_windows_ip()
            and_ip = get_android_ip()
            system_prompt = (
                "You are Mitchell, an autonomous agent. "
                f"Current connected devices: Windows Host ({win_ip}), Android Phone ({and_ip}). "
                "Keep your answers highly concise, hacker-styled, and contextual."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": val}
            ]

            tools = await mcp.list_tools()
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.parameters or {}
                    }
                })

            # Read the selected tier from the Select widget
            model_select = self.app.query_one("#model_select", Select)
            tier = model_select.value

            self.chat_log.write(f"[dim italic yellow]⚡ Using Model Tier: {tier.upper()}[/dim italic yellow]")

            max_turns = 10
            for turn in range(max_turns):
                res = await call(tier, messages=messages, tools=openai_tools)
                messages.append({
                    "role": "assistant",
                    "content": res.content,
                    "tool_calls": res.tool_calls
                })
                
                if res.content:
                    self.chat_log.write(Panel(Markdown(res.content), title="[bold white]Mitchell[/bold white]", border_style="cyan"))

                if not res.tool_calls:
                    break

                for tcall in res.tool_calls:
                    tool_name = tcall.function.name
                    self.chat_log.write(f"[dim yellow]Running tool: {tool_name}[/dim yellow]")
                    try:
                        args = json.loads(tcall.function.arguments)
                        resp = await mcp.call_tool(tool_name, arguments=args)
                        texts = [c.text for c in resp if hasattr(c, 'text')]
                        tool_res_str = "\n".join(texts) if texts else str(resp)
                    except Exception as e:
                        tool_res_str = f"Error executing tool: {e}"
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tcall.id,
                        "name": tool_name,
                        "content": tool_res_str
                    })
                    
        except Exception as e:
            self.chat_log.write(f"[red]Error communicating with LLM: {e}[/red]")

if __name__ == "__main__":
    app = MitchellApp()
    app.run()
