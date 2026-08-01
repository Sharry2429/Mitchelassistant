import os
import sys
import asyncio
from dotenv import load_dotenv

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from openai import AsyncOpenAI

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from google.antigravity.types import McpStdioServer, CustomSystemInstructions

from system_mcp.core.tokens import (
    estimate_tokens, log_token_usage, analyze_prompt, compress_history
)

console = Console()

def load_memory() -> str:
    """Load Mitchell's identity and index from the memory folder."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mitchell_dir = os.path.join(root_dir, ".mitchell")
    
    boot_path = os.path.join(mitchell_dir, "boot.md")
    index_path = os.path.join(mitchell_dir, "index.md")
    
    prompt_parts = ["You are Mitchell AI, a highly capable peak assistant."]
    
    if os.path.exists(boot_path):
        with open(boot_path, "r", encoding="utf-8") as f:
            prompt_parts.append("\n=== CORE IDENTITY (boot.md) ===\n" + f.read())
            
def get_index_prompt() -> str:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(root_dir, ".mitchell", "index.md")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return "\n=== MEMORY INDEX (index.md) ===\n" + f.read()
    return ""

async def main():
    load_dotenv()
    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        console.print("[red]Error: AICREDITS_API_KEY not found in environment.[/red]")
        sys.exit(1)
        
    llm = AsyncOpenAI(api_key=api_key, base_url="https://api.aicredits.in/v1")
    
    memory_prompt = load_memory()
    
    router_system_prompt = (
        f"{memory_prompt}\n\n"
        "You are the Smart Router. If the user is just chatting or asking questions, reply normally in your character. "
        "If the user asks you to perform ANY action that requires tools (e.g. on their phone, computer, file system, scripts, terminal), "
        "output EXACTLY the phrase: [DELEGATE]"
    )
    
    # Configure AGY for tool execution
    agy_config = LocalAgentConfig(
        system_instructions=CustomSystemInstructions(
            text=f"{memory_prompt}\n\nUse your MCP tools to execute any tasks the user requests."
        ),
        capabilities=CapabilitiesConfig(),
        mcp_servers=[
            McpStdioServer(
                command=sys.executable,
                args=["-m", "system_mcp.mcp_server"]
            ),
            McpStdioServer(
                command="npx",
                args=["-y", "@browsermcp/mcp@0.1.3"]
            )
        ]
    )

    history = []
    
    # Setup Claude-like UI
    style = Style.from_dict({'prompt': 'ansicyan bold'})
    session = PromptSession(style=style)
    
    console.print("\n[bold cyan]=========================================[/bold cyan]")
    console.print("[bold cyan]      Mitchell AI - Peak Assistant       [/bold cyan]")
    console.print("[bold cyan]=========================================[/bold cyan]")
    console.print("[dim]Type 'exit' to quit. (Powered by Luna + AGY Tools)[/dim]\n")

    while True:
        try:
            user_input = await session.prompt_async("\nMitchell> ")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
                
            history.append({"role": "user", "content": user_input})
            history = compress_history(history, threshold=10)
            
            # Analyze prompt to see if we need full index.md context
            needs_context = analyze_prompt(user_input)
            dynamic_memory = memory_prompt
            if needs_context:
                dynamic_memory += get_index_prompt()
            
            router_system_prompt = (
                f"{dynamic_memory}\n\n"
                "You are the Smart Router. If the user is just chatting or asking questions, reply normally in your character. "
                "If the user asks you to perform ANY action that requires tools (e.g. on their phone, computer, file system, scripts, terminal), "
                "output EXACTLY the phrase: [DELEGATE]"
            )
            
            router_messages = [{"role": "system", "content": router_system_prompt}] + history
            
            # Log token usage
            estimated = sum(estimate_tokens(m["content"]) for m in router_messages)
            log_token_usage("router", user_input, estimated)
            
            # 1. Query Luna Model
            router_response = await llm.chat.completions.create(
                model="openai/gpt-5.6-luna", messages=router_messages
            )
            
            router_text = router_response.choices[0].message.content.strip()
            
            # 2. Check for tool delegation
            if "[DELEGATE]" not in router_text:
                console.print()
                console.print(Markdown(router_text))
                history.append({"role": "assistant", "content": router_text})
                continue
                
            # 3. Delegate to AGY (Gemini Pro) for execution
            console.print("\n[dim]🚀 Delegating to Antigravity Execution Core...[/dim]\n")
            
            log_token_usage("agy_core", user_input, estimate_tokens(user_input))
            
            content_str = ""
            async with Agent(agy_config) as agy_agent:
                agent_response = await agy_agent.chat(user_input)
                
                # Stream the markdown response from AGY
                # To support streaming markdown nicely, we could just print raw, 
                # but rich Live is better. For simplicity, we stream raw.
                sys.stdout.write("\033[96m") # Cyan color for AGY execution
                async for token in agent_response:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    content_str += token
                sys.stdout.write("\033[0m\n")
                
            history.append({"role": "assistant", "content": f"[Executed via AGY]\n{content_str}"})

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            
    print("\nGoodbye!")

def cli():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    cli()
