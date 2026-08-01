import json
import os
import subprocess
import urllib.request


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Git command failed: {' '.join(args)}\nError: {result.stderr}")
    return result.stdout.strip()

def get_current_branch() -> str:
    return run_git(["branch", "--show-current"])

def create_branch(branch_name: str):
    run_git(["checkout", "-b", branch_name])

def commit_changes(message: str, files: list[str]):
    if get_current_branch() == "main":
        raise Exception("Cannot commit directly to main branch in autonomous mode. Create a branch first.")
        
    from system_mcp.core.self_audit import run_tests
    test_errors = run_tests()
    if test_errors:
        raise Exception("Pre-commit checks failed! Fix these tests before committing:\n" + "\n".join(test_errors))
        
    if not files:
        raise Exception("No files specified for commit.")
        
    for f in files:
        run_git(["add", f])
        
    run_git(["commit", "-m", message])

def push_branch(branch_name: str):
    run_git(["push", "-u", "origin", branch_name])

def open_pr(title: str, body: str, head_branch: str, base_branch: str = "main") -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. Cannot open PR.")
        return None
        
    repo_url = run_git(["config", "--get", "remote.origin.url"])
    # Example format: https://github.com/Sharry2429/Mitchelassistant.git
    # Extract owner/repo
    if "github.com" not in repo_url:
        print(f"Warning: Not a GitHub repo: {repo_url}")
        return None
        
    parts = repo_url.replace(".git", "").split("/")
    owner_repo = f"{parts[-2]}/{parts[-1]}"
    
    api_url = f"https://api.github.com/repos/{owner_repo}/pulls"
    
    data = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }
    
    req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            print(f"✅ Successfully opened PR: {res_data.get('html_url')}")
            return res_data.get('html_url')
    except Exception as e:
        print(f"Error opening PR: {e}")
        return None
