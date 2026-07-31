#!/usr/bin/env python3
"""
Mitchell CLI - Advanced AI Coding & God-Mode OS Assistant
An open-source alternative to Claude Code and Google Antigravity CLI.
"""

import os
import sys
import asyncio
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from system_mcp.mitchell_cli.ui import MitchellUI
from system_mcp.mitchell_cli.agent import MitchellAgent
from system_mcp.mitchell_cli.commands import SlashCommandHandler

SLASH_COMMANDS = [
    "/help", "/plan", "/goal", "/tools", "/compact", "/model", "/remote", "/clear", "/exit", "/quit"
]

def create_prompt_session():
    """Safely creates a PromptSession if interactive console is attached."""
    if not sys.stdin.isatty():
        return None
    try:
        history_file = os.path.expanduser("~/.mitchell_history")
        return PromptSession(
            history=FileHistory(history_file),
            completer=WordCompleter(SLASH_COMMANDS, ignore_case=True)
        )
    except Exception:
        return None

async def get_user_input(session_prompt, prompt_text="\nmitchell ❯ "):
    """Gets input via PromptSession if available, or falls back to sys.stdin.readline."""
    if session_prompt is not None:
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: session_prompt.prompt(prompt_text)
        )
    else:
        print(prompt_text, end="", flush=True)
        line = await asyncio.get_event_loop().run_in_executor(
            None, lambda: sys.stdin.readline()
        )
        if not line:
            raise EOFError()
        return line.strip()

async def main():
    parser = argparse.ArgumentParser(description="Mitchell CLI - AI Coding & God-Mode OS Assistant")
    parser.add_argument("--query", type=str, help="Run a single prompt and exit")
    parser.add_argument("--model", type=str, default="gpt-4o", help="LLM model name")
    parser.add_argument("--remote", action="store_true", help="Start in Remote Host agent mode")
    parser.add_argument("--relay", type=str, default=os.environ.get("RELAY_URL", "ws://127.0.0.1:8765"), help="Relay server URL")
    args = parser.parse_args()

    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("\n[!] Error: AICREDITS_API_KEY environment variable not set.")
        print("    Set it using: setx AICREDITS_API_KEY \"your_key_here\"\n")
        sys.exit(1)

    if args.remote:
        from system_mcp.remote.host_agent import RemoteHostAgent
        agent = RemoteHostAgent(api_key=api_key, relay_url=args.relay)
        await agent.run()
        return

    agent = MitchellAgent(api_key=api_key, model_name=args.model)
    session_prompt = create_prompt_session()

    # Initialize MCP Subprocess for God-Mode tools
    server_params = StdioServerParameters(
        command="python",
        args=["system_mcp/mcp_server.py"],
        env=os.environ.copy()
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as mcp_session:
                await mcp_session.initialize()
                
                try:
                    mcp_tools = await mcp_session.list_tools()
                    mcp_tool_count = len(mcp_tools.tools)
                except Exception:
                    mcp_tool_count = 0
                    
                total_tools = len(agent.coding_tools_schema) + mcp_tool_count

                if sys.stdin.isatty():
                    os.system("cls" if os.name == "nt" else "clear")
                MitchellUI.print_banner(model_name=agent.model_name, tool_count=total_tools)

                if args.query:
                    await agent.process_user_input(args.query, mcp_session)
                    return

                while True:
                    try:
                        user_input = await get_user_input(session_prompt)
                        user_input = user_input.strip()
                        if not user_input:
                            continue

                        handled = await SlashCommandHandler.handle_command(user_input, agent)
                        if not handled:
                            await agent.process_user_input(user_input, mcp_session)

                    except (KeyboardInterrupt, EOFError):
                        MitchellUI.print_info("\nExiting Mitchell CLI.")
                        break
    except Exception as e:
        MitchellUI.print_error(f"Could not connect to System-MCP server: {e}")
        MitchellUI.print_info("Starting in Standalone Coding Agent Mode...")
        
        MitchellUI.print_banner(model_name=agent.model_name, tool_count=len(agent.coding_tools_schema))
        
        if args.query:
            await agent.process_user_input(args.query, None)
            return

        while True:
            try:
                user_input = await get_user_input(session_prompt)
                user_input = user_input.strip()
                if not user_input:
                    continue
                    
                handled = await SlashCommandHandler.handle_command(user_input, agent)
                if not handled:
                    await agent.process_user_input(user_input, None)
            except (KeyboardInterrupt, EOFError):
                MitchellUI.print_info("\nExiting Mitchell CLI.")
                break

if __name__ == "__main__":
    asyncio.run(main())
