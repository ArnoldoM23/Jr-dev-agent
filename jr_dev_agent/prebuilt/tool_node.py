from typing import Any, Dict, List, Callable

class ToolNode:
    """
    Stub for LangGraph ToolNode.
    
    This class acts as a placeholder for the LangGraph ToolNode
    to ensure compatibility with existing imports.
    """
    
    def __init__(self, tools: List[Callable]):
        self.tools = tools
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tools"""
        # Stub implementation
        return state

