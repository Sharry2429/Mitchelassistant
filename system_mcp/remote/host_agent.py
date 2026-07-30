import os
import sys
import json
import asyncio
import base64
import websockets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

class RemoteHostAgent:
    def __init__(self, api_key: str, relay_url: str = "ws://127.0.0.1:8765"):
        self.api_key = api_key
        self.relay_url = relay_url
        self.llm = AsyncOpenAI(api_key=api_key, base_url="https://api.aicredits.in/v1")
        self.key_path = os.path.expanduser("~/.system_mcp_remote_key_aes")
        self.pairing_key = self._load_or_generate_key()
        self.aesgcm = AESGCM(self.pairing_key)
        self.room_id = base64.urlsafe_b64encode(os.urandom(6)).decode('utf-8')

    def _load_or_generate_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read().strip()
        key = AESGCM.generate_key(bit_length=256)
        with open(self.key_path, "wb") as f:
            f.write(key)
        return key

    async def run(self):
        print("=========================================")
        print("      Mitchell AI - Remote Host Agent    ")
        print("=========================================")
        print(f"Relay URL:   {self.relay_url}")
        print(f"Room ID:     {self.room_id}")
        print(f"Pairing Key: {base64.urlsafe_b64encode(self.pairing_key).decode('utf-8')}")
        print("Enter these details in your mobile web app.")
        print("=========================================")

        # Start MCP Server Subprocess
        server_params = StdioServerParameters(
            command="python",
            args=["system_mcp/mcp_server.py"],
            env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
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

                print(f"Loaded {len(openai_tools)} tools.")

                while True:
                    try:
                        async with websockets.connect(self.relay_url) as websocket:
                            print("Connected to relay server.")
                            # Register as host
                            await websocket.send(json.dumps({
                                "type": "register",
                                "role": "host",
                                "room": self.room_id
                            }))

                            # Listen for messages
                            async for message in websocket:
                                try:
                                    data = json.loads(message)
                                    if data.get("type") == "message":
                                        encrypted_payload = data.get("payload")
                                        if encrypted_payload:
                                            raw = base64.b64decode(encrypted_payload)
                                            nonce, ciphertext = raw[:12], raw[12:]
                                            decrypted = self.aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
                                            payload_data = json.loads(decrypted)
                                            user_input = payload_data.get("prompt")
                                            if user_input:
                                                print(f"Remote User: {user_input}")
                                                await self._process_prompt(user_input, session, openai_tools, websocket)
                                except Exception as e:
                                    print(f"Error processing message: {e}")
                                    
                    except websockets.exceptions.ConnectionClosed:
                        print("Disconnected from relay server, reconnecting in 5s...")
                        await asyncio.sleep(5)
                    except Exception as e:
                        print(f"Connection error: {e}")
                        await asyncio.sleep(5)

    async def _send_reply(self, websocket, text: str):
        payload = json.dumps({"reply": text})
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, payload.encode('utf-8'), None)
        encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
        await websocket.send(json.dumps({
            "type": "message",
            "room": self.room_id,
            "payload": encrypted
        }))

    async def _process_prompt(self, user_input: str, session, openai_tools, websocket):
        messages = [{
            "role": "system",
            "content": "You are Mitchell AI, remotely controlled by the user. You have God-Mode access to their devices. Keep responses concise."
        }, {
            "role": "user", 
            "content": user_input
        }]

        while True:
            response = await self.llm.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=openai_tools
            )
            
            message = response.choices[0].message
            msg_dict = {"role": "assistant"}
            if message.content:
                msg_dict["content"] = message.content
            if message.tool_calls:
                msg_dict["tool_calls"] = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
            messages.append(msg_dict)
            
            if not message.tool_calls:
                print(f"Mitchell: {message.content}")
                await self._send_reply(websocket, message.content)
                break
                
            for tool_call in message.tool_calls:
                print(f"[Executing: {tool_call.function.name}]")
                await self._send_reply(websocket, f"[Executing {tool_call.function.name}...]")
                try:
                    args = json.loads(tool_call.function.arguments)
                    result = await session.call_tool(tool_call.function.name, arguments=args)
                    content_str = "\n".join([c.text for c in result.content if hasattr(c, 'text')])
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": content_str})
                except Exception as e:
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": f"Error: {e}"})

if __name__ == "__main__":
    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("Missing AICREDITS_API_KEY")
        sys.exit(1)
    agent = RemoteHostAgent(api_key=api_key)
    asyncio.run(agent.run())
