"""
system_mcp.core.memory
Self-evolving memory tools for Mitchell to update its character and user context.
"""

import os

from system_mcp.core.result import MCPResult

MITCHELL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".mitchell"))

def update_mitchell_memory(topic: str, insights: str) -> MCPResult:
    """
    Updates Mitchell's internal memory files based on behavioral analysis.
    
    Args:
        topic (str): Either 'user_behavior' or 'character'.
        insights (str): The new traits, preferences, or rules to add.
    """
    if not os.path.exists(MITCHELL_DIR):
        return MCPResult.fail(f".mitchell directory not found at {MITCHELL_DIR}. Has it been initialized?")
        
    if topic == "user_behavior":
        target_file = os.path.join(MITCHELL_DIR, "personal", "profile.md")
        header = "\n## Evolved User Insights\n"
    elif topic == "character":
        target_file = os.path.join(MITCHELL_DIR, "boot.md")
        header = "\n## Evolved Character Traits\n"
    else:
        return MCPResult.fail("Topic must be 'user_behavior' or 'character'")
        
    try:
        # Check if the file already has the header
        file_content = ""
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                file_content = f.read()
                
        mode = "a"
        if not os.path.exists(target_file):
            mode = "w"
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
        with open(target_file, mode, encoding="utf-8") as f:
            if header not in file_content:
                f.write(header)
            f.write(f"- {insights}\n")
            
        return MCPResult.success(f"Successfully updated memory topic '{topic}' in {os.path.basename(target_file)}")
    except Exception as e:
        return MCPResult.fail(f"Failed to update memory: {e!s}")
