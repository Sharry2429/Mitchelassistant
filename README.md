# Mitchell

**Mitchell** is an autonomous agent framework that plans, executes, verifies,
and budgets its own work across **Windows**, **Android**, and the **browser** —
and delegates coding to **Hermes-Agent** as its coding worker. It is designed to
run **unattended** (a headless queue-draining worker with self-recovery) and to
answer simple tasks **fast** (a single-round-trip path).

## Project state

| Area | Status | Notes |
|---|---|---|
| Core loop (plan → execute → verify → budget) | ✅ | planner + executor + agent_pool + budget |
| Verification | ✅ | Levels 0–4 (runs, real assertions, rubric, adversarial, device) |
| Memory | ✅ | SQLite 3-store (episodic / semantic / procedural) + promotion |
| Self-skills | ✅ | verified runs save reusable plans; retrieval before tasks |
| Tool Foundry | ✅ | detect gap → Hermes drafts → test gate → register → callable |
| Coding (via Hermes) | ✅ | `hermes chat -q` subprocess worker + `hermes_*` tool gateway |
| Tool surface | ✅ | 300+ MCP tools: Windows, android, browser, core, foundry, hermes |
| Fast interface | ✅ | `mitchell do "<task>"` (fast path → full loop fallback) |
| Unattended worker | ✅ | `python -m mitchell.agent_loop --safe` |
| Watchdog | ✅ | battery/power alerts |
| Review pipeline | ✅ | cheap-iterative → expensive-final → fixes |
| Self-repair | ✅ | sandbox patch → verify → revertible commit → bounded escalate |
| Self-optimization | ✅ | ground-truth cost/latency tuning (periodic) |
| Butler / always-on | ✅ | startup registration + recovery + continuity |

## Requirements

- Python 3.11+
- An API key (default provider endpoint: `AICREDITS_BASE_URL`) set as `AICREDITS_API_KEY`
- `adb` on PATH for Android control (wireless adb over Tailscale/WiFi supported)
- Playwright + chromium for browser control (`python -m playwright install chromium`)

## Install

```bash
# from the repo root
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Quick start — one interface

Just tell Mitchell. `mitchell do` is the single entry point that routes
everything automatically:

```bash
mitchell-do                                        # chat REPL: just type
mitchell-do "open https://example.com and report the title"   # browser
mitchell-do "check the android battery"                        # android
mitchell-do "implement a fibonacci function in fib.py"        # coding -> Hermes
```

Routing, no matter what you say:
- **coding** intent          -> Hermes-Agent coding worker
- **browser / Windows / Android** -> a lean agent loop that starts on the cheap
  **executor (deepseek)** model, escalates to a stronger model, then the full
  verified planner→executor loop, **only when the cheap pass can't answer**.
- Everyday chat is fast and cheap; harder tasks pull more power on demand.

## Controlling the phone (wireless adb over Tailscale)

USB once, then wireless forever:

```bash
# 1) plug the phone in over USB once, enable USB debugging, then:
python -c "from mitchell.android.wireless import setup; print(setup())"
#    -> enables wireless adb, connects to the phone's Tailscale IP, returns target
adb connect <device-ip>:5555          # if you prefer to do it by hand
export ANDROID_SERIAL=<ip>:5555        # point Mitchell at the wireless device
# 2) now unplug the USB — Mitchell keeps the phone over the tailnet
```

## Unattended / always-on

```bash
python -m mitchell.agent_loop --safe          # headless queue-draining worker (safe tools)
python -m mitchell.butler                      # run the always-on butler (recover + watchdog + drain)
```

The butler registers itself to auto-start (Windows Startup), recovers tasks
interrupted by a crash/restart, and resumes from the last checkpoint.

## Environment

- `AICREDITS_API_KEY` — provider key (required)
- `MITCHELL_BUDGET_CAP` — spend cap in USD (default `5.0`); the budget meter
  reads the real token log so a call is refused once spend reaches the cap
- `ANDROID_SERIAL` — target adb device for Android tool calls

## Development

```bash
python -m pytest tests/ -q
```

## License

MIT
