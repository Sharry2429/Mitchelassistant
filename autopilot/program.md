# Mitchelassistant Autopilot

You are running a bounded, repeatable improvement loop on this repo. Follow this
exactly — do not improvise scope.

## Loop

1. Run `python3 autopilot/check.py` and read the current score + breakdown.
2. Pick exactly ONE item from the breakdown to address. Prefer, in order:
   `missing_in_kotlin` items (these are live bugs) > `escaped_interpolation_hits`
   > `orphan_candidates` > `ruff_findings` > `unused_in_python` (these are lowest
   priority — verify with the human before deleting anything flagged here, since
   it might be an intentionally unfinished feature, not dead code).
3. Make the smallest possible fix for that ONE item, touching as few files as
   possible (target: 1 file, hard cap: 3 files, hard cap: 40 changed lines).
4. Re-run `python3 autopilot/check.py`.
5. **Keep** the change only if: the targeted item is resolved, AND no new item
   appears in the breakdown that wasn't there before, AND the total score did not
   increase. Otherwise **discard**: `git checkout -- <files>` and move on.
6. Append one line to `autopilot/experiments.jsonl` regardless of outcome:
   `{"ts": "...", "target": "...", "files": [...], "score_before": N,
   "score_after": N, "kept": true|false, "note": "one sentence"}`.
7. If kept, commit with a message referencing the experiment
   (`git commit -m "autopilot: fix X (score N->M)"`). Never push directly to
   `main`; push to a dedicated `autopilot/<date>` branch only.
8. Repeat from step 1 for a fixed number of iterations (default: 10) or until
   `score == 0` and every `unused_in_python` item has been reviewed by a human,
   whichever comes first. Then stop and summarize.

## Hard rules — do not violate these regardless of how promising an idea seems

- **Never add a new top-level directory, new third-party service, new runtime
  dependency, or new file that isn't a direct, minimal fix for the one item
  you're targeting.** This repo has already had an agent quietly ship a relay
  server, a web client, and a CLI package alongside a requested fix. That is
  exactly what this rule exists to prevent. If you think a bigger change is
  warranted, stop and write it up as a suggestion in `experiments.jsonl` instead
  of implementing it.
- **Never touch `system_mcp/android/connection.py`'s Tailscale block** (the
  `_TAILSCALE_HOST`/`_TAILSCALE_PORT`/`_connect_tailscale` code) unless the
  experiment you're on is explicitly about that block.
- **Never invoke real ADB, real phone actions, or any function in
  `system_mcp/windows/` or `system_mcp/android/` that isn't `check.py` itself.**
  This loop edits and scores code; it does not operate a live device.
- **Never claim a build succeeded** (Gradle/Kotlin compiles, APK installs)
  unless you actually ran that tool in this environment and it produced real
  output. If the toolchain isn't available, say so in the experiment note.
- If `check.py` itself needs a fix, that's a valid experiment target too — but
  treat changes to the scorer with extra scrutiny, since a broken scorer can
  silently approve bad changes.
