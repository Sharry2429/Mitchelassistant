import os
import glob
import subprocess
import json
from typing import Dict, Any, List

class LocalCodingTools:
    """Local workspace coding agent tools matching Claude Code & AGY features."""

    @staticmethod
    def view_file(filepath: str, start_line: int = 1, end_line: int = 800) -> str:
        """View file contents with line numbers."""
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            
            selected_lines = lines[start_idx:end_idx]
            output = []
            for idx, line in enumerate(selected_lines, start=start_idx + 1):
                output.append(f"{idx:4d} | {line.rstrip()}")
                
            header = f"=== File: {filepath} (Showing lines {start_idx + 1}-{end_idx} of {total_lines}) ===\n"
            return header + "\n".join(output)
        except Exception as e:
            return f"Error reading file '{filepath}': {e}"

    @staticmethod
    def edit_file(filepath: str, target_content: str, replacement_content: str) -> str:
        """Edit file by replacing exact target string with replacement content."""
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if target_content not in content:
                return f"Error: Target content not found in '{filepath}'. Please view the file to verify exact content."
                
            count = content.count(target_content)
            if count > 1:
                return f"Error: Target content appears {count} times in '{filepath}'. Specify a more unique target block."
                
            new_content = content.replace(target_content, replacement_content, 1)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return f"Successfully updated '{filepath}'."
        except Exception as e:
            return f"Error editing file '{filepath}': {e}"

    @staticmethod
    def write_file(filepath: str, content: str) -> str:
        """Write content to a file (create or overwrite)."""
        try:
            dirname = os.path.dirname(filepath)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)
                
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote file '{filepath}'."
        except Exception as e:
            return f"Error writing file '{filepath}': {e}"

    @staticmethod
    def list_dir(directory: str = ".", recursive: bool = False) -> str:
        """List contents of a directory."""
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' does not exist."
        try:
            items = []
            if recursive:
                for root, dirs, files in os.walk(directory):
                    rel_root = os.path.relpath(root, directory)
                    if rel_root == ".":
                        rel_root = ""
                    for f in files[:100]:
                        items.append(os.path.join(rel_root, f))
            else:
                for entry in os.listdir(directory)[:100]:
                    full_p = os.path.join(directory, entry)
                    kind = "[DIR] " if os.path.isdir(full_p) else "[FILE]"
                    items.append(f"{kind} {entry}")
                    
            return f"Contents of '{directory}':\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing directory '{directory}': {e}"

    @staticmethod
    def grep_search(query: str, search_path: str = ".") -> str:
        """Search for a text pattern across workspace files."""
        matches = []
        try:
            for root, _, files in os.walk(search_path):
                if ".git" in root or "__pycache__" in root or "node_modules" in root:
                    continue
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for idx, line in enumerate(f, start=1):
                                if query.lower() in line.lower():
                                    matches.append(f"{filepath}:{idx}: {line.strip()[:120]}")
                                    if len(matches) >= 50:
                                        break
                    except Exception:
                        pass
                if len(matches) >= 50:
                    break
            if not matches:
                return f"No matches found for pattern '{query}'."
            return f"Found {len(matches)} matches for '{query}':\n" + "\n".join(matches)
        except Exception as e:
            return f"Error executing search: {e}"

    @staticmethod
    def run_command(command: str, cwd: str = ".") -> str:
        """Execute a shell/terminal command."""
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            code = res.returncode
            
            output_parts = [f"Exit Code: {code}"]
            if out:
                output_parts.append(f"STDOUT:\n{out[:2000]}")
            if err:
                output_parts.append(f"STDERR:\n{err[:2000]}")
            return "\n".join(output_parts)
        except subprocess.TimeoutExpired:
            return f"Error: Command '{command}' timed out after 60 seconds."
        except Exception as e:
            return f"Error executing command: {e}"

def get_coding_tools_schema() -> List[Dict[str, Any]]:
    """Return OpenAI function definitions for coding agent tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "view_file",
                "description": "View file contents with line numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute or relative file path"},
                        "start_line": {"type": "integer", "description": "Starting line number (1-based)", "default": 1},
                        "end_line": {"type": "integer", "description": "Ending line number", "default": 800}
                    },
                    "required": ["filepath"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Replace a unique target block in a file with new code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Target file path"},
                        "target_content": {"type": "string", "description": "Exact existing code block to replace"},
                        "replacement_content": {"type": "string", "description": "New code block"}
                    },
                    "required": ["filepath", "target_content", "replacement_content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or overwrite a file with full content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "File path"},
                        "content": {"type": "string", "description": "Full file content"}
                    },
                    "required": ["filepath", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List contents of a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory path", "default": "."},
                        "recursive": {"type": "boolean", "description": "Include subdirectories", "default": False}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "Search workspace for text or regex pattern.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text pattern to search for"},
                        "search_path": {"type": "string", "description": "Directory to search", "default": "."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a terminal shell command in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command line string"},
                        "cwd": {"type": "string", "description": "Working directory", "default": "."}
                    },
                    "required": ["command"]
                }
            }
        }
    ]
