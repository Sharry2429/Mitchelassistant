AICREDITS_BASE_URL = "https://api.aicredits.in/v1"

MODEL_TIERS = {
    "ui_vision":      "bytedance/ui-tars-1.5-7b",
    "general_vision": "openai/gpt-5.6-luna",
    "base":           "openai/gpt-5.6-luna",
    "mid":            "openai/gpt-5.6-terra",
    "top":            "openai/gpt-5.6-sol",
    "seed":           "bytedance-seed/seed-1.6-flash",
    "deepseek":       "deepseek/deepseek-v4-flash",
    "gemini":         "google/gemini-flash-latest",
}

# Real per-model pricing, USD per 1M tokens (input/output).
# These are structural — the budget meter must read REAL costs from the routing
# table, not a flat placeholder. Values are per-model overrides; fall back to
# DEFAULT_PRICING when a tier/model is not listed. Set prices precisely later
# from the actual provider's bill; the mechanism is what matters here.
DEFAULT_PRICING = {"input": 0.10, "output": 0.30}

MODEL_PRICING = {
    "openai/gpt-5.6-luna":          {"input": 0.15,  "output": 0.60},
    "openai/gpt-5.6-terra":         {"input": 0.30,  "output": 1.20},
    "openai/gpt-5.6-sol":           {"input": 0.60,  "output": 2.40},
    "bytedance/ui-tars-1.5-7b":     {"input": 0.10,  "output": 0.20},
    "bytedance-seed/seed-1.6-flash":{"input": 0.05,  "output": 0.15},
    "deepseek/deepseek-v4-flash":   {"input": 0.02,  "output": 0.05},
    "google/gemini-flash-latest":   {"input": 0.075, "output": 0.30},
}


def pricing_for(model: str) -> dict:
    """Return {input, output} USD-per-1M-token pricing for a model."""
    return MODEL_PRICING.get(model, DEFAULT_PRICING)
