"""
Tool execution engine for WinControl.
Dispatches tool calls to the appropriate underlying functions.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional

from system_mcp.windows.schema import _discover_modules, _get_public_functions

__all__ = [
    "execute_tool",
    "execute_tools",
    "get_tool_function",
    "validate_arguments",
    "ToolNotFoundError",
    "ToolExecutionError"
]

class ToolNotFoundError(Exception):
    """Raised when a requested tool does not exist."""
    pass

class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""
    pass

# Global lazily-initialized registry mapping tool name -> function
_TOOL_REGISTRY: Optional[Dict[str, Callable]] = None

def _get_registry() -> Dict[str, Callable]:
    """Lazily build the tool registry."""
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        _TOOL_REGISTRY = {}
        modules = _discover_modules()
        for mod_name, module in modules.items():
            funcs = _get_public_functions(module)
            for func_name, func in funcs.items():
                if func_name in _TOOL_REGISTRY:
                    # Resolve collision by keeping the existing one,
                    # but exposing module-prefixed names for both
                    old_func = _TOOL_REGISTRY[func_name]
                    old_mod = inspect.getmodule(old_func)
                    old_mod_name = old_mod.__name__.split('.')[-1] if old_mod else "unknown"
                    _TOOL_REGISTRY[f"{old_mod_name}.{func_name}"] = old_func
                    _TOOL_REGISTRY[f"{mod_name}.{func_name}"] = func
                else:
                    _TOOL_REGISTRY[func_name] = func
    return _TOOL_REGISTRY

def get_tool_function(name: str) -> Callable:
    """Get the actual function object for a tool name."""
    registry = _get_registry()
    if name not in registry:
        raise ToolNotFoundError(f"Tool '{name}' not found.")
    return registry[name]

def validate_arguments(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce arguments for a tool using its signature."""
    func = get_tool_function(name)
    sig = inspect.signature(func)
    
    validated = {}
    for param_name, param in sig.parameters.items():
        if param_name in arguments:
            val = arguments[param_name]
            if param.annotation != inspect.Parameter.empty:
                try:
                    if param.annotation == int and not isinstance(val, int):
                        val = int(val)
                    elif param.annotation == float and not isinstance(val, float):
                        val = float(val)
                    elif param.annotation == bool and not isinstance(val, bool):
                        if isinstance(val, str):
                            val = val.lower() in ('true', '1', 't', 'y', 'yes')
                        else:
                            val = bool(val)
                except (ValueError, TypeError):
                    pass # Keep original value and let it fail on execution if invalid
            validated[param_name] = val
        elif param.default == inspect.Parameter.empty:
            raise ToolExecutionError(f"Missing required argument: {param_name}")
            
    return validated

def execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
    """Dispatch a tool call by name with arguments."""
    arguments = arguments or {}
    try:
        func = get_tool_function(name)
        validated_args = validate_arguments(name, arguments)
        return func(**validated_args)
    except ToolNotFoundError:
        raise
    except Exception as e:
        raise ToolExecutionError(f"Failed to execute tool '{name}': {str(e)}") from e

def execute_tools(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute multiple tool calls and gather results."""
    results = []
    for call in tool_calls:
        name = call.get('name')
        args = call.get('arguments', {})
        if not name:
            results.append({
                "name": "unknown",
                "result": None,
                "error": "Missing 'name' field in tool call."
            })
            continue
            
        try:
            res = execute_tool(name, args)
            results.append({
                "name": name,
                "result": res,
                "error": None
            })
        except Exception as e:
            results.append({
                "name": name,
                "result": None,
                "error": str(e)
            })
            
    return results
