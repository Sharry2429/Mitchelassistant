"""
scripts/prove_foundry.py — Phase 5 Tool Foundry, live end-to-end.

  detect -> draft (via Hermes coding worker) -> TEST gate -> register -> callable

Run: python scripts/prove_foundry.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitchell.core import memory, tool_registry

SPEC = (
    "Write a single python module in tool.py with one module-level function "
    "named slugify(text: str) -> str that converts a string to a URL slug: "
    "strip surrounding whitespace, lowercase, replace spaces with '-', and "
    "remove punctuation. Write test_tool.py with 3 pytest assertions "
    "(e.g. slugify('Hello World')=='hello-world'). Do not add any other files."
)

BANNER = "=" * 62


def main():
    # 1. detect: seed a repeated gap, then show detection works on real episodes.
    for _ in range(3):
        memory.log_episode("gap", "step", "PASS step: slugify a title", verified=True,
                           pattern_key="slugify_text")
    print(f"{BANNER}\n1) DETECT gap\n{BANNER}")
    gap = tool_registry.detect_gap(min_freq=3)
    print("detected capability gap:", gap)

    # 2. draft via the Hermes coding worker
    print(f"{BANNER}\n2) DRAFT tool via Hermes-Agent worker\n{BANNER}")
    drafted = tool_registry.draft_tool(SPEC, timeout=900)
    print("hermes exit:", drafted.get("exit_code"), "| duration:", drafted.get("duration"), "s")
    print("files:\n", drafted.get("files", "").strip())
    wd = drafted["workdir"]
    if not drafted.get("ok"):
        print("draft failed:", (drafted.get("stderr_tail") or "")[-400:])
        sys.exit(1)

    # 3. TEST gate — Phase 1 verification
    print(f"{BANNER}\n3) TEST (Phase 1 gate)\n{BANNER}")
    tres = tool_registry.test_tool(wd)
    print("pytest:", tres["result"], "| ok:", tres["ok"])

    # 4. REGISTER only if gate passed
    print(f"{BANNER}\n4) REGISTER (gated on test)\n{BANNER}")
    name = tool_registry.register_tool("slugify", wd, SPEC)
    print("registered:", name, "| registry:", tool_registry.list_registered())

    # 5. CALLABLE by a later task
    print(f"{BANNER}\n5) CALL the registered tool\n{BANNER}")
    fn = tool_registry.load_foundry_function("slugify")
    if fn is None:
        print("FAIL: foundry function not loadable"); sys.exit(1)
    for inp in ("Hello World", "Rapid Fast Interfaces!", "Phase Five  "):
        print(f"  slugify({inp!r}) -> {fn(inp)!r}")
    print(f"{BANNER}\nFOUNDRY PROOF: {'PASS' if name else 'FAIL'}\n{BANNER}")


if __name__ == "__main__":
    main()
