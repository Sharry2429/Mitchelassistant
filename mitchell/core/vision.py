import base64
import io
from PIL import Image
from mitchell.core.llm_client import call
import json

def preprocess_screenshot(image_path: str, max_dim: int = 1024) -> str:
    with Image.open(image_path) as img:
        width, height = img.size
        if width > max_dim or height > max_dim:
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

async def get_action(goal: str, screenshot_b64: str, task_id: str | None = None) -> dict:
    prompt = f"Goal: {goal}\nWhere is the target and what should I do?"
    messages = [{"role": "user", "content": prompt}]
    
    result = await call("ui_vision", messages=messages, image_b64=screenshot_b64, task_id=task_id)
    
    try:
        data = json.loads(result.content)
        return {
            "action": data.get("action", "click"),
            "coordinates": data.get("coordinates", [0, 0]),
            "confidence": data.get("confidence", 1.0)
        }
    except Exception:
        return {"action": "click", "coordinates": [0,0], "confidence": 0.5}

async def execute_ui_step(goal: str, screenshot_path: str, task_id: str | None = None, is_visual_task: bool = False):
    tree_accessible = not is_visual_task
    
    if tree_accessible:
        # Mocking tree extraction preference
        tree_result = None 
        if tree_result:
            return tree_result
            
    b64 = preprocess_screenshot(screenshot_path)
    return await get_action(goal, b64, task_id)
