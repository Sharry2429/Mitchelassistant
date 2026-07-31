import os
import sys
import asyncio
import argparse
import time

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from openai import AsyncOpenAI
from dotenv import load_dotenv

COSTS_USD = {
    "openai/gpt-5.6-luna": {"in": 0.150 / 1e6, "out": 0.600 / 1e6},
}
INR_RATE = 83.5


def print_telemetry(model, duration, usage):
    if not usage:
        return
    in_t = usage.prompt_tokens
    out_t = usage.completion_tokens
    total = in_t + out_t
    cost = 0.0
    if model in COSTS_USD:
        cost = (
            in_t * COSTS_USD[model]["in"] + out_t * COSTS_USD[model]["out"]
        ) * INR_RATE
    print(
        f"\033[90m[⏱ Time: {duration:.1f}s | 🪙 Tokens: {total} | 💸 Cost: ₹{cost:.4f}]\033[0m"
    )


async def auto_optimize_task(history, llm, kb_path):
    recent = history[-10:] if len(history) > 10 else history
    prompt = "You are an Auto-Researcher. Review this recent interaction log. Did the assistant encounter any errors (e.g. tool execution failed) and figure out a workaround, or learn anything specific about the user's phone state or UI quirks? If yes, write a concise, one-sentence rule to help the assistant in the future (e.g. 'Always wait 2 seconds before clicking X'). If there are no new significant learnings, output exactly 'NONE'."

    msgs = [{"role": "system", "content": prompt}]
    for m in recent:
        content = m.get("content", "")
        if content:
            msgs.append({"role": m.get("role", "user"), "content": content[:1000]})

    try:
        resp = await llm.chat.completions.create(
            model="openai/gpt-5.6-luna", messages=msgs
        )
        content = resp.choices[0].message.content.strip()
        if content and content != "NONE" and "[DELEGATE]" not in content:
            with open(kb_path, "a") as f:
                f.write("- " + content + "\n")
            print(f"\n\033[32m[Auto-Researcher learned: {content}]\033[0m")
    except Exception:
        pass


load_dotenv()


async def main():
    parser = argparse.ArgumentParser(description="Mitchell AI - Peak Assistant")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Start in Remote Host mode (connects to relay server)",
    )
    parser.add_argument(
        "--relay",
        type=str,
        default=os.environ.get("RELAY_URL", "ws://127.0.0.1:8765"),
        help="Relay server WS URL",
    )
    parser.add_argument(
        "--query", type=str, help="Run a single command instead of interactive loop"
    )
    args = parser.parse_args()

    api_key = os.environ.get("AICREDITS_API_KEY")
    if not api_key:
        print("Error: AICREDITS_API_KEY not found in environment or .env file.")
        sys.exit(1)

    if args.remote:
        from system_mcp.remote.host_agent import RemoteHostAgent

        agent = RemoteHostAgent(api_key=api_key, relay_url=args.relay)
        await agent.run()
        return

    print("=========================================")
    print("      Mitchell AI - Peak Assistant       ")
    print("=========================================")
    print("Starting lightweight router...")

    llm = AsyncOpenAI(api_key=api_key, base_url="https://api.aicredits.in/v1")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(script_dir, "system_mcp", "knowledge_base.txt")
    kb_content = ""
    if os.path.exists(kb_path):
        with open(kb_path, "r") as f:
            kb_content = f.read().strip()

    base_system_prompt = "You are Mitchell AI, a highly capable peak assistant."
    if kb_content:
        base_system_prompt += f"\n\nFollow these learned rules strictly:\n{kb_content}"

    router_system_prompt = f"{base_system_prompt} You are the Smart Router. If the user is just chatting, reply normally. If the user asks you to perform ANY action (on their phone, computer, or coding), output EXACTLY the phrase: [DELEGATE]"

    history = []

    if args.query:
        print(f"You: {args.query}")
        user_input = args.query
        history.append({"role": "user", "content": user_input})

    print("Type 'exit' to quit.\n")

    while True:
        try:
            if not args.query:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                history.append({"role": "user", "content": user_input})

            router_messages = [
                {"role": "system", "content": router_system_prompt}
            ] + history
            start_t = time.time()
            router_response = await llm.chat.completions.create(
                model="openai/gpt-5.6-luna", messages=router_messages
            )
            end_t = time.time()
            print_telemetry(
                "openai/gpt-5.6-luna", end_t - start_t, router_response.usage
            )

            router_text = router_response.choices[0].message.content.strip()

            if "[DELEGATE]" not in router_text:
                print(f"\nMitchell: {router_text}\n")
                history.append({"role": "assistant", "content": router_text})
                if args.query:
                    break
                continue

            # Delegate to AGY Python SDK
            print(
                "\n🚀 [Delegating to AGY Python SDK (Gemini Pro) for zero-cost execution]..."
            )

            agent_config = LocalAgentConfig(
                system_instructions="You are an expert automation assistant. Use your tools to fulfill the request. Be concise.",
                capabilities=CapabilitiesConfig(),
            )

            content_str = ""
            async with Agent(agent_config) as agy_agent:
                agent_response = await agy_agent.chat(user_input)

                print("\n[AGY Thinking/Executing]:")
                async for token in agent_response:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    content_str += token
                print()

            history.append(
                {"role": "assistant", "content": f"[Executed via AGY]\n{content_str}"}
            )

            # Spawn auto-optimizer task in background
            asyncio.create_task(auto_optimize_task(list(history), llm, kb_path))

            if args.query:
                break

        except KeyboardInterrupt:
            print("\nExiting Mitchell AI.")
            break


if __name__ == "__main__":
    asyncio.run(main())
