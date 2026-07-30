import os
import sys
import json
import asyncio
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("Error: AICREDITS_API_KEY environment variable not set.")
        print("Please set it in your environment using: setx AICREDITS_API_KEY \"your_key\"")
        sys.exit(1)

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
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "System-MCP action",
                        "parameters": t.inputSchema
                    }
                })
                
            print(f"Successfully loaded {len(openai_tools)} God-Mode tools.")
            print("Type 'exit' to quit.\n")
            
            messages = [{
                "role": "system",
                "content": "You are Mitchell AI, a highly capable peak assistant with God-Mode access to the user's Android phone and Windows PC. You can place calls, send WhatsApp messages, control the screen, launch apps, and manage settings. Be concise and execute the user's requests."
            }]
            
            while True:
                try:
                    user_input = input("You: ")
                    if user_input.lower() in ['exit', 'quit']:
                        break
                        
                    messages.append({"role": "user", "content": user_input})
                    
                    while True:
                        response = await llm.chat.completions.create(
                            model="gpt-4o",
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
