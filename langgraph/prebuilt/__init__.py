"""
Minimal stub of ``langgraph.prebuilt`` exposing :class:`ToolNode`.

The real package includes many rich prebuilt nodes.  For the Jr Dev Agent we
just need a thin wrapper that calls the provided function.
"""

from typing import Any, Callable, Dict


class ToolNode:
    """
    Simple callable node that forwards to the provided handler.
    """

    def __init__(self, tool: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.tool = tool

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.tool(state)
