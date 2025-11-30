"""
Lightweight local stub of the external `langgraph` package.

This project normally depends on the real `langgraph` library, but that
binary is unavailable in this environment.  To keep the MCP server and
tests working we provide just enough structure to satisfy the pieces of
the API that our code uses.

The implementation is intentionally minimal: it supports registering nodes,
defining linear and conditional edges, compiling the graph, and executing
it asynchronously.  Only the functionality required by the Jr Dev Agent
workflow is implemented.
"""

from .graph import StateGraph, START, END

__all__ = ["StateGraph", "START", "END"]
