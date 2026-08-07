# MITCHELL — ONE-SHOT REMAINING-BUILD PROMPT (for Claude)

You are finishing the "Mitchell" autonomous-agent codebase. Below is the exact
project layout and the complete remaining scope. Implement ALL items in ONE
pass with real, working Python. Do not stub; leave no TODO. Match the existing
style and contracts exactly. Add pytest tests for each feature in `tests/`.
All code lives in the repo that contains this file. Work autonomously and run
the tests at the end.

## PROJECT LAYOUT (existing, do not break)
- mitchell/core/tasks.py        -> Task/TaskStep dataclasses; list_tasks(); task_all_terminal()
- mitchell/core/executor.py     -> execute_task(); worker_loop(); run_step(); recover_interrupted_tasks(); _safe_log_episode()
- mitchell/core/planner.py      -> create_plan(); PlanningError
- mitchell/core/agent_pool.py   -> claim_next_step(); mark_step_completed(); mark_step_failed(); TaskLock/DeviceLock
- mitchell/core/verify.py       -> verify_step() Levels 0-1 (uses args["expect_file_exists"]/_expect_process_running); MCPResult
- mitchell/core/budget.py       -> check_budget_before_call(); estimate_cost(); total_spend(); BUDGET_CAP
- mitchell/core/models.py       -> MODEL_TIERS (role->model); MODEL_PRICING; pricing_for()
- mitchell/core/llm_client.py   -> call(role, messages, tools, task_id) -> LLMResult(content, tool_calls); real cost logged
- mitchell/core/memory.py + memory_store.py -> SQLite 3-store (episodic/semantic/procedural); log_episode(); promote_verified_patterns(); save_task_pattern(); find_cached_plan(); retrieve_schema()
- mitchell/core/tool_provider.py   -> ToolProvider protocol; MCPToolProvider; StaticToolProvider
- mitchell/core/safe_provider.py   -> SafeProvider; is_safe(name) allowlist (blocks destructive)
- mitchell/core/tool_registry.py   -> detect_gap(); draft_tool(); test_tool(); register_tool(); load_foundry_function()
- mitchell/core/fast.py            -> fast_do() lean loop
- mitchell/core/do.py              -> `mitchell do "<task>"` CLI (coding->Hermes, else fast path->full loop)
- mitchell/core/hermes_coder.py / hermes_gateway.py -> delegate to `hermes chat -q` subprocess; hermes_* tools
- mitchell/core/browser/browser.py -> Playwright DOM tools
- mitchell/mcp_server.py           -> registers all MCP tools; _register_foundry_tools(); _register_hermes_tools()
- mitchell/agent_loop.py           -> worker process; supports --safe
- tests/                           -> pytest suite (currently green)
- data dirs: ~/.system-mcp/tasks/ (task JSON queue); ~/.system-mcp/memory/mitchell.db (SQLite); ~/.system-mcp/coding/

## HARD RULES (non-negotiable)
1. No fake results: every feature must produce real, observable output.
2. Verification-gated: nothing (skills, tools, self-patches) is trusted unless
   it passed real tests/checks. Self-optimization may read ONLY ground-truth
   signals (real token counts, real wall-clock, real pass/fail).
3. Self-repair patches apply in a SANDBOX copy first, pass the full verify
   pipeline, every patch is a revertible git commit, and after a bounded number
   of failed attempts it stops, reverts to last-known-good, and escalates
   (never loops forever).
4. Budget: use budget.py check_budget_before_call; cost from MODEL_PRICING.
5. Use SafeProvider (no destructive tools) for any unattended/autonomous path
   unless explicitly overridden.

## SCOPE — implement ALL of these

### 1) BATTERY/POWER WATCHDOG (mitchell/core/watchdog.py)
- Functions: `battery_status()` (laptop: psutil battery; Android: via android
  tools/adb battery level), `check_thresholds(laptop_lt=50, phone_lt=20)`,
  `proactive_alert(msg)` (write to a log and return the message; if a hermes_
  notify tool exists, prefer calling it; no hard console dependency).
- `run_once()` returns a list of produced alerts. `run_loop(interval=300)` polls.
- Simulate thresholds in tests (monkeypatch battery_status) and assert the
  correct alert text is emitted when laptop<50 or phone<20.
- Thread into an unattended loop (see Butler).

### 2) REVIEW PIPELINE (mitchell/core/review.py)
- Configure agent_pool+routing as a workflow: `iterative_review(diff/code)` runs
  a cheap model ("mid") in a loop until it reports no issues (max N iterations);
  then ONE expensive "top" (Sol) final pass; then collect the issues and
  implement fixes via the executor.
- Functions: `iterative_review(text)`, `final_review(text)`, `apply_fixes(issues)`.
- Tests: with mocked LLM, assert order (mid loop then single top call) and that
  a fix task is emitted for flagged issues; caps iterations.

### 3) SELF-REPAIR (mitchell/core/self_repair.py)
- `detect()`: scan episodic log + recent task failures + health checks for
  crash/exception signals.
- `diagnose(crash_context)`: reason over crash log + recent changes; return
  likely cause (via llm_client call).
- `patch_in_sandbox(repo_dir)`: copy repo to a temp sandbox, apply a candidate
  patch produced by diagnosis there.
- `verify_patch(sandbox)`: run the repo's test suite (pytest) + self_audit in
  the sandbox; only proceed if green.
- `deploy_patch(sandbox)`: revertible git commit; record commit hash.
- `bounded_escalate(...)`: after MAX_ATTEMPTS (default 3) without a verified
  fix, revert to last-known-good commit and return an escalation object.
- Tests: a deliberately-introduced bug is detected, patched in sandbox,
  verified, and a commit exists (mock the actual patch apply); a deliberately
  unfixable bug escalates instead of looping (assert it returns after bounded
  attempts).

### 4) SELF-OPTIMIZATION (mitchell/core/self_optimize.py)
- Only ground-truth inputs: token log (~/.system-mcp/tokens.jsonl), real
  wall-clock timings, pass/fail from verification.
- `analyze_ground_truth()` -> per-task-type cost+latency stats.
- `config_suggestion()`: propose tier/routing tweaks (e.g. move high-volume
  executor steps to a cheaper tier) ONLY when supported by the data.
- `apply_suggestion()` applies a config change and records a before/after.
- `run_job()` is periodic (not continuous). Test with synthetic ground-truth
  log: assert a real improvement metric is computed from the log, not self-report.

### 5) BUTLER / ALWAYS-ON (mitchell/core/butler.py + mitchell/supervisor.py)
- `ensure_startup_register()`: register an OS auto-start entry on Windows
  (Task Scheduler via schtasks / or appdata Startup shortcut) idempotently;
  on any OS fall back to a documented manual step. Never guess credentials.
- `run_butler()`: a continuous supervisor that (a) recovers interrupted tasks,
  (b) drains the task queue unattended (use worker_loop queue mode with
  SafeProvider), (c) runs the watchdog loop, (d) resumes from checkpoints on
  restart (recover_interrupted_tasks).
- `continuity_guarantee()` documented/verified: kill mid-task, restart, resumes.
- Tests: simulate kill+restart (a task with a RUNNING step) and assert resume;
  assert register call is idempotent (mock subprocess).

### 6) FINISH MULTI-MODEL ROUTING (mitchell/core/models.py routing)
- Add cost-aware downgrade routing: when remaining budget is low, executor
  auto-downgrades high-volume tiers to cheaper models via MODEL_PRICING.
- `select_model(role, remaining_budget)` in models.py: if remaining budget <
  threshold, pick cheapest tier that satisfies the role capability; else the
  table mapping. Keep vision/UI roles pinned (never downgrade a vision role to
  a text model).
- Tests: assert downgrade picks a cheaper model at low budget and never maps a
  vision role to a text model.

### 7) FINISH VERIFICATION LEVELS 2-4 (mitchell/core/verify.py)
- Extend verify_step with optional rubric + adversarial review:
  - L2: `verify_against_rubric(step, transcript, rubric)` -> rubric score/pass.
  - L3: `adversarial_review(transcript)` -> one cross-model review call returning
    issues list; returns (passed, issues).
  - L4: `device_verify(step)` -> for android steps, re-read device state (e.g.
    foreground app actually matches expected) before declaring pass.
- Keep backward compatible (Levels 0-1 unchanged). Tests for each new level with
  mocked calls.

## ACCEPTANCE / DONE
- All modules import cleanly; no new hard deps beyond the existing/provided ones.
- `python -m pytest tests/ -q` passes with the new tests included.
- Each feature has at least one real test; the watchdog thresholds, self-repair
  escalation, budget downgrade, and contiguity-resume are all demonstrably
  asserted.
- No TODOs/stubs; no fabricated results (tests must mock the LLM tool, and the
  mock must be explicit).
