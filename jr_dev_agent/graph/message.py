"""
Stub helpers for message utilities used by the legacy code.

The real LangGraph library exposes structured message handling utilities.
Our workflow only needs to append messages into a list stored on the state.
"""

from typing import Any, Dict, List


def add_messages(state: Dict[str, Any], messages: List[Any]) -> Dict[str, Any]:
    """Append messages to ``state['messages']`` and return the updated state."""
    if not messages:
        return state
    state.setdefault("messages", [])
    state["messages"].extend(messages)
    return state

