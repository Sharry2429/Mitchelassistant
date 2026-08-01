"""
system_mcp.core.result
Unified result envelope for all System-MCP operations.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class MCPResult:
    """Standard return envelope for every public System-MCP function.

    Attributes:
        ok:    True when the operation succeeded, False otherwise.
        data:  Payload on success (type varies per operation).
        error: Human-readable error message on failure, None on success.
    """

    ok: bool = True
    data: Any = None
    error: str | None = None

    # ---- convenience constructors ----

    @classmethod
    def success(cls, data: Any = None) -> "MCPResult":
        return cls(ok=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "MCPResult":
        return cls(ok=False, error=error)

    def to_dict(self) -> dict:
        """Serialize to a plain dict (for JSON transport)."""
        d: dict[str, Any] = {"ok": self.ok}
        if self.data is not None:
            d["data"] = self.data
        if self.error is not None:
            d["error"] = self.error
        return d
