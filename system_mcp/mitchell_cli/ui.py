import os
import sys
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.style import Style

# Force UTF-8 stdout/stderr encoding on Windows if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(force_terminal=True if sys.stdout.isatty() else False)

class MitchellUI:
    """Rich Terminal User Interface for Mitchell CLI."""
    
    @staticmethod
    def print_banner(model_name: str = "gpt-4o", god_mode: bool = True, tool_count: int = 0):
        banner_text = Text()
        banner_text.append("   ___  ___ _____ _____ _____ _____ _     _    \n", style="bold cyan")
        banner_text.append("   |  \\/  |_   _|_   _/  ___/  ___| |   | |   \n", style="bold cyan")
        banner_text.append("   | .  . | | |   | | \\ `--.\\ `--.| |   | |   \n", style="bold blue")
        banner_text.append("   | |\\/| | | |   | |  `--. \\`--. \\ |   | |   \n", style="bold blue")
        banner_text.append("   | |  | |_| |_  | | /\\__/ /\\__/ / |___| |___\n", style="bold magenta")
        banner_text.append("   \\_|  |_/\\___/  \\_/ \\____/\\____/\\_____/\\____/\n", style="bold magenta")
        
        status_line = f"[bold white]Mitchell CLI v1.0.0[/bold white] | [bold green]Model:[/bold green] {model_name} | [bold yellow]God-Mode:[/bold yellow] {'ACTIVE' if god_mode else 'DISABLED'} | [bold magenta]Tools:[/bold magenta] {tool_count} loaded"
        
        panel = Panel(
            Text.assemble(banner_text, "\n", Text.from_markup(status_line)),
            border_style="cyan",
            title="[bold bright_white]AI Coding & OS Automation Assistant[/bold bright_white]",
            subtitle="[italic grey70]Type /help for slash commands | /exit to quit[/italic grey70]"
        )
        console.print(panel)

    @staticmethod
    def print_user_prompt():
        cwd = os.path.basename(os.getcwd()) or os.getcwd()
        console.print(f"\n[bold bright_blue]mitchell[/bold bright_blue] [grey50]({cwd})[/grey50] [bold bright_cyan]>[/bold bright_cyan] ", end="")

    @staticmethod
    def print_assistant_message(content: str):
        console.print("\n[bold magenta]Mitchell:[/bold magenta]")
        md = Markdown(content)
        console.print(md)

    @staticmethod
    def print_tool_start(tool_name: str, args: Dict[str, Any]):
        args_summary = ", ".join([f"{k}={repr(v)[:40]}" for k, v in args.items()])
        console.print(Panel(
            f"[bold yellow]Executing:[/bold yellow] [bold white]{tool_name}[/bold white]\n[grey70]Args: {args_summary}[/grey70]",
            border_style="yellow",
            padding=(0, 1)
        ))

    @staticmethod
    def print_tool_result(tool_name: str, result: str, is_error: bool = False):
        border = "red" if is_error else "green"
        title = "Tool Error" if is_error else "Tool Output"
        
        # Truncate output preview for clean CLI look
        preview = result[:800] + ("\n... [truncated]" if len(result) > 800 else "")
        console.print(Panel(
            Text(preview, style=border),
            title=f"[bold {border}]{title}: {tool_name}[/bold {border}]",
            border_style=border,
            padding=(0, 1)
        ))

    @staticmethod
    def print_diff(filename: str, old_content: str, new_content: str):
        console.print(f"\n[bold yellow]File Modified:[/bold yellow] [bold white]{filename}[/bold white]")
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff_text = Text()
        max_lines = max(len(old_lines), len(new_lines))
        for i in range(min(max_lines, 30)):
            old_l = old_lines[i] if i < len(old_lines) else None
            new_l = new_lines[i] if i < len(new_lines) else None
            
            if old_l == new_l:
                diff_text.append(f"  {new_l}\n", style="grey70")
            else:
                if old_l is not None:
                    diff_text.append(f"- {old_l}\n", style="bold red")
                if new_l is not None:
                    diff_text.append(f"+ {new_l}\n", style="bold green")
                    
        if max_lines > 30:
            diff_text.append("... [remaining diff omitted]\n", style="italic grey50")
            
        console.print(Panel(diff_text, border_style="blue", title=f"Diff: {filename}"))

    @staticmethod
    def print_plan(title: str, steps: List[str]):
        table = Table(title=f"[bold cyan]Plan: {title}[/bold cyan]", border_style="cyan", show_header=True)
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Step / Description", style="white")
        table.add_column("Status", style="green", width=12)
        
        for idx, step in enumerate(steps, 1):
            table.add_row(str(idx), step, "Pending")
            
        console.print(table)

    @staticmethod
    def print_btw_response(question: str, answer: str):
        console.print(Panel(
            Markdown(answer),
            title=f"[bold magenta]BTW Side-Note: {question[:50]}[/bold magenta]",
            subtitle="[italic grey70]This side-question was answered without modifying main chat history.[/italic grey70]",
            border_style="magenta"
        ))

    @staticmethod
    def print_help():
        table = Table(title="[bold cyan]Mitchell CLI Slash Commands[/bold cyan]", border_style="cyan")
        table.add_column("Command", style="bold yellow", width=18)
        table.add_column("Description", style="white")
        
        table.add_row("/help", "Show this help menu")
        table.add_row("/btw <question>", "Ask a quick side question without polluting main task history")
        table.add_row("/plan <task>", "Enter Planner Mode to design step-by-step before coding")
        table.add_row("/goal <goal>", "Enter Goal Verification Mode for autonomous task completion")
        table.add_row("/rules", "Reload or display .mitchellrules / project instructions")
        table.add_row("/tools", "List all available Coding and God-Mode tools")
        table.add_row("/compact", "Compact & summarize conversation history to save tokens")
        table.add_row("/model <name>", "Switch LLM model (e.g., gpt-4o, claude-3-5-sonnet)")
        table.add_row("/remote [url]", "Toggle or set Remote Host Relay server connection")
        table.add_row("/clear", "Clear terminal screen and reset chat display")
        table.add_row("/exit", "Exit Mitchell CLI")
        
        console.print(table)

    @staticmethod
    def print_info(msg: str):
        console.print(f"[bold blue][i][/bold blue] {msg}")

    @staticmethod
    def print_success(msg: str):
        console.print(f"[bold green][+][/bold green] {msg}")

    @staticmethod
    def print_error(msg: str):
        console.print(f"[bold red][X][/bold red] {msg}")
