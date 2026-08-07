import os
from openai import AsyncOpenAI
from mitchell.core.models import AICREDITS_BASE_URL, MODEL_TIERS, select_model
from mitchell.core.budget import check_budget_before_call, log_usage, estimate_cost, remaining_budget
from dataclasses import dataclass

@dataclass
class LLMResult:
    content: str
    tool_calls: list | None = None

_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("AICREDITS_API_KEY")
        if not api_key:
            raise ValueError("AICREDITS_API_KEY environment variable is not set")
        _client = AsyncOpenAI(base_url=AICREDITS_BASE_URL, api_key=api_key)
    return _client

async def call(role: str, messages: list, tools: list | None = None,
               image_b64: str | None = None, task_id: str | None = None) -> LLMResult:
    if role not in MODEL_TIERS:
        raise ValueError(f"Unknown role: {role}")
    
    # Cost-aware routing: downgrade high-volume roles when remaining budget is low.
    model = select_model(role, remaining_budget())
    
    # Enforce budget before call
    check_budget_before_call(role, task_id)
    
    client = get_client()
    
    # If image_b64 is provided, append it to the last user message
    if image_b64:
        last_msg = messages[-1]
        if isinstance(last_msg.get("content"), str):
            last_msg["content"] = [
                {"type": "text", "text": last_msg["content"]},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]

    kwargs = {
        "model": model,
        "messages": messages,
    }
    
    if tools:
        kwargs["tools"] = tools

    response = await client.chat.completions.create(**kwargs)
    
    message = response.choices[0].message
    content = message.content or ""
    tool_calls = message.tool_calls
    
    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0
    # Real cost from the routing table's per-model pricing — not a flat placeholder.
    cost_estimate = estimate_cost(model, prompt_tokens, completion_tokens)

    log_usage(task_id, role, model, prompt_tokens, completion_tokens, cost_estimate)
    
    return LLMResult(content=content, tool_calls=tool_calls)
