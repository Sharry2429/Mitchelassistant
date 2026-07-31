import os
import sys
from typing import Optional
from system_mcp.mitchell_cli.ui import MitchellUI
from system_mcp.mitchell_cli.agent import MitchellAgent

class SlashCommandHandler:
    """Parses and executes Mitchell CLI slash commands."""

    @staticmethod
    async def handle_command(cmd_input: str, agent: MitchellAgent) -> bool:
        """
        Returns True if command was handled, False if input is a normal prompt.
        Returns 'exit' signal if user issued /exit.
        """
        cmd_input = cmd_input.strip()
        if not cmd_input.startswith("/"):
            return False

        parts = cmd_input.split(" ", 1)
        command = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if command in ["/exit", "/quit"]:
            MitchellUI.print_info("Goodbye! Exiting Mitchell CLI.")
            sys.exit(0)

        elif command == "/help":
            MitchellUI.print_help()
            return True

        elif command == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            MitchellUI.print_banner(model_name=agent.model_name, tool_count=len(agent.coding_tools_schema))
            return True

        elif command == "/compact":
            agent.compact_history()
            return True

        elif command == "/plan":
            if not args:
                MitchellUI.print_error("Usage: /plan <task description>")
            else:
                await agent.run_plan_mode(args)
            return True

        elif command == "/goal":
            if not args:
                MitchellUI.print_error("Usage: /goal <objective description>")
            else:
                await agent.run_goal_mode(args)
            return True

        elif command == "/model":
            if not args:
                MitchellUI.print_info(f"Current model: {agent.model_name}")
                MitchellUI.print_info("Usage: /model <model_name> (e.g. gpt-4o, claude-3-5-sonnet, gemini-1.5-pro)")
            else:
                agent.model_name = args
                MitchellUI.print_success(f"Switched model to '{agent.model_name}'")
            return True

        elif command == "/tools":
            MitchellUI.print_info("Available Coding Agent Tools:")
            for t in agent.coding_tools_schema:
                fn = t["function"]
                MitchellUI.print_info(f"  • [bold white]{fn['name']}[/bold white]: {fn['description']}")
            return True

        elif command == "/remote":
            if args:
                os.environ["RELAY_URL"] = args
                MitchellUI.print_success(f"Set RELAY_URL to '{args}'")
            else:
                current_url = os.environ.get("RELAY_URL", "ws://127.0.0.1:8765")
                MitchellUI.print_info(f"Current Remote Relay URL: {current_url}")
            return True

        else:
            MitchellUI.print_error(f"Unknown command '{command}'. Type /help for available slash commands.")
            return True
