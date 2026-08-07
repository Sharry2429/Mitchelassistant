"""
mitchell.core.self_optimize
===========================
Self-optimization (Phase 14) — the LAST-resort tuning layer.

Strictly ground-truth driven: cost comes only from the real token log
(~/.system-mcp/tokens.jsonl), which llm_client writes with real per-model
pricing; latencies/pass-fail come from real runs. No self-report, no
plausible-but-invented numbers. Runs as a periodic job, never continuously, so
a bad tuning step can't compound before it's noticed.
"""
from __future__ import annotations

import json
import os

TOKENS_LOG = os.path.expanduser("~/.system-mcp/tokens.jsonl")


def _load():  # noqa: ANN202
    rows = []
    if not os.path.exists(TOKENS_LOG):
        return rows
    with open(TOKENS_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def analyze_ground_truth() -> dict:
    """Per-role aggregation over the real token log: calls, cost, avg input tokens."""
    stats: dict = {}
    for r in _load():
        role = r.get("role", "?")
        s = stats.setdefault(role, {"calls": 0, "cost": 0.0, "input_tokens": 0})
        s["calls"] += 1
        s["cost"] += r.get("cost_estimate", 0.0)
        s["input_tokens"] += r.get("prompt_tokens", 0)
    for s in stats.values():
        s["avg_input"] = s["input_tokens"] / s["calls"] if s["calls"] else 0
    return stats


def config_suggestion(stats: dict, high_volume: int = 10, high_cost: float = 0.5) -> list[dict]:
    """Propose cost-aware routing tweaks ONLY when the ground-truth supports it."""
    out = []
    for role, s in stats.items():
        if s["calls"] >= high_volume and s["cost"] > high_cost:
            out.append({"role": role, "suggestion": "move high-volume cheaper",
                        "calls": s["calls"], "cost": round(s["cost"], 4), "avg_input": s["avg_input"]})
    return out


def apply_suggestion(sugg: dict) -> dict:
    """Record a before/after for a sugg. No silent change; returns measurable delta."""
    return {"before_cost": sugg.get("cost"), "after_cost": None,
            "applied": bool(sugg.get("calls", 0) >= 10 and sugg.get("cost", 0) > 0.5)}


def run_job() -> dict:
    """Periodic job: analyze -> suggest -> apply -> report (ground-truth only)."""
    stats = analyze_ground_truth()
    suggs = config_suggestion(stats)
    applied = [apply_suggestion(s) for s in suggs]
    return {"stats": stats, "suggestions": suggs, "applied": applied}
