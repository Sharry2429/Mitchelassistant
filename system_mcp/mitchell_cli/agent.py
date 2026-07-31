import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from system_mcp.mitchell_cli.ui import MitchellUI
from system_mcp.mitchell_cli.tools import LocalCodingTools, get_coding_tools_schema

SYSTEM_PROMPT = """You are Mitchell, an elite AI coding assistant and OS-level operator. You possess:
1. Full Coding Agent capabilities: Viewing, editing, searching, and managing project files, as well as executing shell commands.
2. God-Mode OS capabilities: Deep Windows and Android automation (calling, Messaging, UI vision, touch, settings).

GUIDELINES:
- Be concise, direct, and pragmatic.
- Inspect files and search code before writing changes.
- Use exact edits when modifying files.
- Always verify your work by running commands or inspecting file states.
"""

class MitchellAgent:
    """Core Agent execution loop managing LLM calls, tool routing, and modes."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        self.api_key = api_key
        self.model_name = model_name
        self.llm = AsyncOpenAI(api_key=api_key, base_url="https://api.aicredits.in/v1")
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.mode = "act"  # "act", "plan", or "goal"
        self.coding_tools_schema = get_coding_tools_schema()
        self.all_tools_schema: List[Dict[str, Any]] = list(self.coding_tools_schema)
        self.mcp_session: Optional[ClientSession] = None
        self.god_mode_active = False
        self.load_project_rules()

    def load_project_rules(self):
        """Loads .mitchellrules, .agentrules, or AGENT.md if present in workspace."""
        rule_files = [".mitchellrules", ".agentrules", "AGENT.md", ".cursorrules"]
        loaded_rules = []
        for rf in rule_files:
            if os.path.exists(rf):
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            loaded_rules.append(f"--- Project Rules ({rf}) ---\n{content}")
                except Exception:
                    pass
        if loaded_rules:
            combined_rules = "\n\n".join(loaded_rules)
            self.messages[0]["content"] += f"\n\nPROJECT RULES & WORKFLOWS:\n{combined_rules}"
            MitchellUI.print_info("Loaded custom project rules into system prompt.")

    async def process_btw_question(self, question: str):
        """Processes a quick side question without altering main conversation history."""
        MitchellUI.print_info(f"Answering BTW side question...")
        btw_messages = [
            {"role": "system", "content": "You are Mitchell. Answer this quick side question concisely and accurately."},
            {"role": "user", "content": question}
        ]
        try:
            response = await self.llm.chat.completions.create(
                model=self.model_name,
                messages=btw_messages
            )
            answer = response.choices[0].message.content or "No response generated."
            MitchellUI.print_btw_response(question, answer)
        except Exception as e:
            MitchellUI.print_error(f"Error processing BTW question: {e}")

    async def initialize_mcp(self):
        """Attempts to connect to System-MCP server for God-Mode OS capabilities."""
        try:
            server_params = StdioServerParameters(
                command="python",
                args=["system_mcp/mcp_server.py"],
                env=os.environ.copy()
            )
            # We connect via stdio
            self.mcp_params = server_params
            self.god_mode_active = True
        except Exception as e:
            MitchellUI.print_error(f"God-Mode System-MCP initialization error: {e}")
            self.god_mode_active = False

    def compact_history(self):
        """Compacts conversation history to conserve context window."""
        if len(self.messages) <= 4:
            MitchellUI.print_info("History is already minimal.")
            return

        system_msg = self.messages[0]
        recent_msgs = self.messages[-4:]
        
        summary_msg = {
            "role": "user",
            "content": f"[System Note: Earlier conversation history of {len(self.messages) - 5} messages was compacted to conserve context memory.]"
        }
        
        self.messages = [system_msg, summary_msg] + recent_msgs
        MitchellUI.print_success(f"Compacted conversation history! New length: {len(self.messages)} messages.")

    async def execute_local_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Routes execution to local coding agent tools."""
        if name == "view_file":
            return LocalCodingTools.view_file(**args)
        elif name == "edit_file":
            old_c = LocalCodingTools.view_file(args.get("filepath", ""))
            res = LocalCodingTools.edit_file(**args)
            new_c = LocalCodingTools.view_file(args.get("filepath", ""))
            MitchellUI.print_diff(args.get("filepath", ""), old_c, new_c)
            return res
        elif name == "write_file":
            return LocalCodingTools.write_file(**args)
        elif name == "list_dir":
            return LocalCodingTools.list_dir(**args)
        elif name == "grep_search":
            return LocalCodingTools.grep_search(**args)
        elif name == "run_command":
            return LocalCodingTools.run_command(**args)
        else:
            return f"Error: Local tool '{name}' not found."

    async def process_user_input(self, user_input: str, session: Optional[ClientSession] = None):
        """Executes a single user interaction loop through the LLM."""
        self.messages.append({"role": "user", "content": user_input})
        
        # Load God-Mode tools if available
        tools = list(self.coding_tools_schema)
        if session:
            try:
                mcp_tools = await session.list_tools()
                for t in mcp_tools.tools:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "System-MCP action",
                            "parameters": t.inputSchema
                        }
                    })
            except Exception:
                pass
                
        # Limit tool count to fit OpenAI tool limits (max 128)
        tools = tools[:120]

        while True:
            try:
                response = await self.llm.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    tools=tools if tools else None
                )
                
                message = response.choices[0].message
                msg_dict = {"role": "assistant"}
                if message.content:
                    msg_dict["content"] = message.content
                if message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                self.messages.append(msg_dict)
                
                if message.content:
                    MitchellUI.print_assistant_message(message.content)
                    
                if not message.tool_calls:
                    break
                    
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except Exception:
                        args = {}
                        
                    MitchellUI.print_tool_start(fn_name, args)
                    
                    # Execute tool locally or via MCP session
                    if fn_name in [t["function"]["name"] for t in self.coding_tools_schema]:
                        result = await self.execute_local_tool(fn_name, args)
                    elif session:
                        try:
                            mcp_res = await session.call_tool(fn_name, arguments=args)
                            result = "\n".join([c.text for c in mcp_res.content if hasattr(c, 'text')])
                        except Exception as e:
                            result = f"MCP Error: {e}"
                    else:
                        result = f"Error: Tool '{fn_name}' not available."
                        
                    is_err = result.startswith("Error")
                    MitchellUI.print_tool_result(fn_name, result, is_error=is_err)
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": result
                    })
            except Exception as e:
                MitchellUI.print_error(f"LLM API Error: {e}")
                break

    async def run_plan_mode(self, task: str, session: Optional[ClientSession] = None):
        """Generates a structured step-by-step implementation plan before execution."""
        MitchellUI.print_info(f"Entering Planner Mode for task: '{task}'")
        prompt = f"Plan out the following task step-by-step before writing code: {task}"
        await self.process_user_input(prompt, session)

    async def run_goal_mode(self, goal: str, session: Optional[ClientSession] = None):
        """Runs autonomous goal verification loop until the task is complete."""
        MitchellUI.print_info(f"Entering Goal Mode: '{goal}'")
        goal_prompt = f"GOAL: {goal}. Implement this goal autonomously. Test and verify your changes after editing."
        await self.process_user_input(goal_prompt, session)
