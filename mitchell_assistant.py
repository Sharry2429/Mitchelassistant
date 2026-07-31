import os
import sys
import json
import asyncio
import argparse
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from dotenv import load_dotenv

load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="Mitchell AI - Peak Assistant")
    parser.add_argument("--remote", action="store_true", help="Start in Remote Host mode (connects to relay server)")
    parser.add_argument("--relay", type=str, default=os.environ.get("RELAY_URL", "ws://127.0.0.1:8765"), help="Relay server WS URL")
    parser.add_argument("--query", type=str, help="Run a single command instead of interactive loop")
    args = parser.parse_args()

    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("Error: AICREDITS_API_KEY not found in environment or .env file.")
        print("Please add it to the .env file in the root directory: AICREDITS_API_KEY=\"your_key_here\"")
        sys.exit(1)

    if args.remote:
        from system_mcp.remote.host_agent import RemoteHostAgent
        agent = RemoteHostAgent(api_key=api_key, relay_url=args.relay)
        await agent.run()
        return

    print("=========================================")
    print("      Mitchell AI - Peak Assistant       ")
    print("=========================================")
    print("Connecting to System-MCP Server...")
    
    llm = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.aicredits.in/v1"
    )
    
    # We run the mcp_server.py as a subprocess using stdio
    server_params = StdioServerParameters(
        command="python",
        args=["system_mcp/mcp_server.py"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Connected! Loading System-MCP tools...")
            tools_response = await session.list_tools()
            
            openai_tools = []
            for t in tools_response.tools:
                # Filter to avoid OpenAI's 128 tool limit
                if t.name.startswith("android_interaction") or t.name.startswith("android_apps") or t.name.startswith("android_communication") or t.name.startswith("android_system"):
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "System-MCP action",
                            "parameters": t.inputSchema
                        }
                    })
                    
                if len(openai_tools) >= 120:
                    break
                
            print(f"Successfully loaded {len(openai_tools)} God-Mode tools.")
            print("Type 'exit' to quit.\n")
            
            messages = [{
                "role": "system",
                "content": "You are Mitchell AI, a highly capable peak assistant with God-Mode access to the user's Android phone and Windows PC. You can place calls, send WhatsApp messages, control the screen, launch apps, and manage settings. Be concise and execute the user's requests."
            }]
            
            if args.query:
                print(f"You: {args.query}")
                user_input = args.query
                messages.append({"role": "user", "content": user_input})
            
            while True:
                try:
                    if not args.query:
                        user_input = input("You: ")
                        if user_input.lower() in ['exit', 'quit']:
                            break
                        messages.append({"role": "user", "content": user_input})
                    
                    while True:
                        response = await llm.chat.completions.create(
                            model="openai/gpt-5.6-luna",
                            messages=messages,
                            tools=openai_tools
                        )
                        
                        message = response.choices[0].message
                        # Clean up message for openai parsing rules (cannot append message object directly if it has None fields sometimes)
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
                        messages.append(msg_dict)
                        
                        if not message.tool_calls:
                            print(f"\nMitchell: {message.content}\n")
                            if args.query:
                                return
                            break
                            
                        for tool_call in message.tool_calls:
                            print(f"\n[Executing: {tool_call.function.name}]...")
                            try:
                                args = json.loads(tool_call.function.arguments)
                                result = await session.call_tool(tool_call.function.name, arguments=args)
                                
                                content_str = "\n".join([c.text for c in result.content if hasattr(c, 'text')])
                                print(f"[Result]: {content_str}")
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_call.function.name,
                                    "content": content_str
                                })
                            except Exception as e:
                                error_msg = f"Error calling tool: {e}"
                                print(f"[Error]: {error_msg}")
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_call.function.name,
                                    "content": error_msg
                                })
                except KeyboardInterrupt:
                    print("\nExiting Mitchell AI.")
                    break

if __name__ == "__main__":
    asyncio.run(main())
