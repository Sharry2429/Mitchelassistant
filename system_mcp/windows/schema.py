"""
Schema generation for WinControl tools.
Converts Python function signatures and docstrings into LLM tool schemas.
"""

import inspect
import importlib
import re
import types
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints, get_origin, get_args

__all__ = [
    "get_tools_schema",
    "get_tool_schema",
    "list_tools",
    "get_tool_categories",
]

_MODULES_TO_SCAN = [
    "desktop", "input", "shell", "app", "filesystem", "clipboard",
    "registry", "process", "notification", "display", "scrape",
    "network", "services", "sysinfo", "audio", "power"
]

def _parse_docstring(docstring: str) -> tuple[str, dict[str, str]]:
    """Parse a Google-style docstring to get description and parameter descriptions."""
    if not docstring:
        return "", {}
    
    lines = docstring.strip().split('\n')
    description_lines = []
    param_descriptions = {}
    
    current_section = "description"
    current_param = None
    
    for line in lines:
        line_stripped = line.strip()
        
        if line_stripped in ("Args:", "Arguments:", "Parameters:"):
            current_section = "args"
            continue
        elif line_stripped in ("Returns:", "Raises:", "Yields:", "Examples:"):
            current_section = "other"
            continue
            
        if current_section == "description":
            description_lines.append(line_stripped)
        elif current_section == "args":
            # Match parameter: "param_name (type): description" or "param_name: description"
            param_match = re.match(r"^([a-zA-Z0-9_]+)\s*(?:\([^)]+\))?:\s*(.*)", line_stripped)
            if param_match:
                current_param = param_match.group(1)
                param_descriptions[current_param] = param_match.group(2)
            elif current_param and line_stripped:
                # Continuation of previous parameter description
                param_descriptions[current_param] += " " + line_stripped
                
    description = " ".join(description_lines).strip()
    return description, param_descriptions

def _python_type_to_json_schema(py_type: Any) -> dict:
    """Convert a Python type to a JSON Schema type."""
    if py_type == inspect.Parameter.empty:
        return {"type": "string"}
        
    origin = get_origin(py_type)
    args = get_args(py_type)
    
    if origin is Union:
        # Handle Optional[X] which is Union[X, NoneType]
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _python_type_to_json_schema(non_none_args[0])
        return {"type": "string"}
        
    if origin is list or origin is set or origin is tuple or py_type in (list, set, tuple):
        schema = {"type": "array"}
        if args:
            schema["items"] = _python_type_to_json_schema(args[0])
        else:
            schema["items"] = {"type": "string"}
        return schema
        
    if origin is dict or py_type is dict:
        return {"type": "object"}
        
    if hasattr(py_type, "__name__"):
        type_name = py_type.__name__
        if type_name == 'str':
            return {"type": "string"}
        elif type_name == 'int':
            return {"type": "integer"}
        elif type_name == 'float':
            return {"type": "number"}
        elif type_name == 'bool':
            return {"type": "boolean"}
        elif type_name == 'list':
            return {"type": "array", "items": {"type": "string"}}
        elif type_name == 'dict':
            return {"type": "object"}
            
    # Fallback
    return {"type": "string"}

def _get_public_functions(module: types.ModuleType) -> dict[str, Callable]:
    """Get all public functions from a module."""
    funcs = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith('_'):
            # Only include functions actually defined in this module
            if inspect.getmodule(obj) == module:
                funcs[name] = obj
    return funcs

def _discover_modules() -> dict[str, types.ModuleType]:
    """Dynamically discover wincontrol modules."""
    modules = {}
    for mod_name in _MODULES_TO_SCAN:
        try:
            full_name = f"wincontrol.{mod_name}"
            module = importlib.import_module(full_name)
            modules[mod_name] = module
        except ImportError:
            pass
    return modules

def _generate_raw_schema(func: Callable) -> dict:
    """Generate a generic schema for a function."""
    sig = inspect.signature(func)
    docstring = func.__doc__ or ""
    description, param_descriptions = _parse_docstring(docstring)
    
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}
        
    properties = {}
    required = []
    
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
            
        param_schema = {}
        
        py_type = type_hints.get(name, param.annotation)
        param_schema.update(_python_type_to_json_schema(py_type))
        
        if name in param_descriptions:
            param_schema["description"] = param_descriptions[name]
            
        if param.default == inspect.Parameter.empty:
            required.append(name)
            
        properties[name] = param_schema
        
    return {
        "name": func.__name__,
        "description": description or f"Execute {func.__name__}",
        "properties": properties,
        "required": required
    }

def get_tool_schema(func_name: str, format: str = 'openai') -> dict:
    """Generate schema for a single function by name."""
    modules = _discover_modules()
    target_func = None
    
    for mod_name, module in modules.items():
        funcs = _get_public_functions(module)
        if func_name in funcs:
            target_func = funcs[func_name]
            break
            
    if not target_func:
        raise ValueError(f"Tool {func_name} not found")
        
    raw_schema = _generate_raw_schema(target_func)
    
    if format == 'openai':
        return {
            "type": "function",
            "function": {
                "name": raw_schema["name"],
                "description": raw_schema["description"],
                "parameters": {
                    "type": "object",
                    "properties": raw_schema["properties"],
                    "required": raw_schema["required"]
                }
            }
        }
    elif format == 'anthropic':
        return {
            "name": raw_schema["name"],
            "description": raw_schema["description"],
            "input_schema": {
                "type": "object",
                "properties": raw_schema["properties"],
                "required": raw_schema["required"]
            }
        }
    elif format == 'google':
        return {
            "name": raw_schema["name"],
            "description": raw_schema["description"],
            "parameters": {
                "type": "OBJECT",
                "properties": raw_schema["properties"],
                "required": raw_schema["required"]
            }
        }
    elif format == 'raw':
        return raw_schema
    else:
        raise ValueError(f"Unsupported format: {format}")

def get_tools_schema(format: str = 'openai', modules: Optional[List[str]] = None) -> List[Dict]:
    """Generate tool schemas from all WinControl public functions."""
    all_modules = _discover_modules()
    schemas = []
    
    mods_to_process = modules if modules is not None else list(all_modules.keys())
    
    for mod_name in mods_to_process:
        if mod_name in all_modules:
            module = all_modules[mod_name]
            funcs = _get_public_functions(module)
            for func_name in funcs.keys():
                schemas.append(get_tool_schema(func_name, format=format))
                
    return schemas

def list_tools() -> List[Dict[str, str]]:
    """List all available tools with name and description."""
    modules = _discover_modules()
    tools = []
    
    for mod_name, module in modules.items():
        funcs = _get_public_functions(module)
        for name, func in funcs.items():
            docstring = func.__doc__ or ""
            description, _ = _parse_docstring(docstring)
            tools.append({
                "name": name,
                "description": description or f"Execute {name}"
            })
            
    return tools

def get_tool_categories() -> Dict[str, List[str]]:
    """Group tools by category/module."""
    modules = _discover_modules()
    categories = {}
    
    for mod_name, module in modules.items():
        funcs = _get_public_functions(module)
        categories[mod_name] = list(funcs.keys())
        
    return categories
