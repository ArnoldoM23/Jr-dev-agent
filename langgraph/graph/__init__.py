"""
Minimal stub of ``langgraph.graph`` providing the pieces required by the
Jr Dev Agent codebase.

Only a subset of the real library is implemented: registering nodes,
declaring edges (linear and conditional), compiling, and executing the
graph asynchronously.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

START = "__start__"
END = "__end__"

NodeFunc = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]] | Dict[str, Any]]
ConditionFunc = Callable[[Dict[str, Any]], Awaitable[str] | str]


class CompiledGraph:
    """Executable representation returned by :meth:`StateGraph.compile`."""

    def __init__(self, graph: "StateGraph"):
        self._graph = graph

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        current = self._graph._entry_point
        if current is None:
            raise RuntimeError("StateGraph entry point is not set")

        while current and current != END:
            node_fn = self._graph._nodes.get(current)
            if node_fn is None:
                raise RuntimeError(f"Node '{current}' not registered in StateGraph")

            state = await _maybe_await(node_fn(state))

            if current in self._graph._conditional_edges:
                condition_fn, mapping = self._graph._conditional_edges[current]
                outcome = await _maybe_await(condition_fn(state))
                next_node = mapping.get(outcome)
                if next_node is None:
                    raise RuntimeError(
                        f"Conditional outcome '{outcome}' has no mapping from node '{current}'"
                    )
                current = next_node
                continue

            next_nodes = self._graph._edges.get(current, [])
            if not next_nodes:
                break
            if len(next_nodes) > 1:
                raise RuntimeError(
                    f"Node '{current}' has multiple outgoing edges in stub graph; "
                    "split the flow or use conditional edges."
                )
            current = next_nodes[0]

        return state

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.run(self.ainvoke(state))


class StateGraph:
    """
    Very small subset of the real ``StateGraph`` API.  The type parameter is
    accepted for compatibility but not used.
    """

    def __init__(self, _state_type: Any = None):
        self._nodes: Dict[str, NodeFunc] = {}
        self._edges: Dict[str, List[str]] = defaultdict(list)
        self._conditional_edges: Dict[str, Tuple[ConditionFunc, Dict[str, str]]] = {}
        self._entry_point: Optional[str] = None

    def add_node(self, name: str, func: NodeFunc) -> None:
        self._nodes[name] = func

    def set_entry_point(self, name: str) -> None:
        self._entry_point = name

    def add_edge(self, source: str, target: str) -> None:
        if source == START:
            self.set_entry_point(target)
            return
        self._edges[source].append(target)

    def add_conditional_edges(
        self,
        source: str,
        condition: ConditionFunc,
        mapping: Dict[str, str],
    ) -> None:
        self._conditional_edges[source] = (condition, mapping)

    def compile(self) -> CompiledGraph:
        if self._entry_point is None:
            raise RuntimeError("Cannot compile StateGraph without entry point")
        return CompiledGraph(self)


async def _maybe_await(result: Awaitable[Any] | Any) -> Any:
    if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
        return await result
    return result
