import re
import glob
import json
import subprocess
import os
import datetime

def main():
    # 1. Protocol Consistency
    py_actions = set()
    for f in glob.glob("system_mcp/android/**/*.py", recursive=True):
        try:
            with open(f, encoding="utf-8", errors="ignore") as file:
                text = file.read()
                for m in re.finditer(r"""execute\(\s*['"]([a-zA-Z_]+)['"]""", text):
                    py_actions.add(m.group(1))
        except Exception:
            pass

    kt_actions = set()
    for f in glob.glob("system_mcp/companion/**/*.kt", recursive=True):
        try:
            with open(f, encoding="utf-8", errors="ignore") as file:
                text = file.read()
                for m in re.finditer(r"""ToolRegistry\.register\(\s*['"]([a-zA-Z_]+)['"]""", text):
                    kt_actions.add(m.group(1))
        except Exception:
            pass

    missing_in_kotlin = sorted(py_actions - kt_actions)
    unused_in_python = sorted(kt_actions - py_actions)

    # 2. Escaped-interpolation lint
    escaped_interpolation_hits = []
    pattern = re.compile(r'\\\$(?:\{|[a-zA-Z_])')
    for f in glob.glob("system_mcp/**/*.kt", recursive=True):
        try:
            with open(f, encoding="utf-8", errors="ignore") as file:
                text = file.read()
                matches = pattern.findall(text)
                for _ in matches:
                    escaped_interpolation_hits.append(f)
        except Exception:
            pass

    # 3. Orphan/dead-file detection
    kt_files = glob.glob("system_mcp/companion/app/src/main/java/**/*.kt", recursive=True)
    manifest = ""
    manifest_path = "system_mcp/companion/app/src/main/AndroidManifest.xml"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8", errors="ignore") as f:
                manifest = f.read()
        except Exception:
            pass
    
    all_kt_text = {}
    for f in glob.glob("system_mcp/**/*.kt", recursive=True):
        try:
            with open(f, encoding="utf-8", errors="ignore") as file:
                all_kt_text[f] = file.read()
        except Exception:
            pass

    orphan_candidates = []
    for f in kt_files:
        basename = os.path.basename(f)
        classname = basename.replace(".kt", "")
        
        if classname in manifest:
            continue
            
        referenced = False
        for other_f, text in all_kt_text.items():
            if other_f != f and classname in text:
                referenced = True
                break
                
        if not referenced:
            orphan_candidates.append(f)

    # 4. Static lint counts
    ruff_findings = 0
    cmd = ["ruff", "check", "system_mcp/"]
    if os.path.exists("scripts/"):
        cmd.append("scripts/")
    if os.path.exists("mitchell_assistant.py"):
        cmd.append("mitchell_assistant.py")
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        ruff_findings = len([line for line in result.stdout.splitlines() if ".py:" in line])
    except FileNotFoundError:
        try:
            cmd[0] = "pyflakes"
            result = subprocess.run(cmd, capture_output=True, text=True)
            ruff_findings = len([line for line in result.stdout.splitlines() if ".py:" in line])
            ruff_findings += len([line for line in result.stderr.splitlines() if ".py:" in line])
        except FileNotFoundError:
            pass
            
    # Calculate score
    score = 0
    score += len(missing_in_kotlin) * 10
    score += len(unused_in_python) * 1
    score += len(escaped_interpolation_hits) * 2
    score += len(orphan_candidates) * 3
    score += ruff_findings * 1
    
    # Output format
    output = {
        "score": score,
        "breakdown": {
            "missing_in_kotlin": missing_in_kotlin,
            "unused_in_python": unused_in_python,
            "escaped_interpolation_hits": escaped_interpolation_hits,
            "orphan_candidates": orphan_candidates,
            "ruff_findings": ruff_findings,
            "kotlin_lint": "skipped - toolchain unavailable"
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)
    main()
