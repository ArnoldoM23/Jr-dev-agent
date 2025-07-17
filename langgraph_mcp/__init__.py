"""
🚀 Jr Dev Agent - LangGraph MCP Package
==========================================

This package contains the LangGraph MCP Server implementation for the Jr Dev Agent.
It handles the central orchestration of AI agent workflows including Jira ticket
processing, prompt building, and integration with all system components.

Author: Jr Dev Agent Team
Version: 1.0
"""

__version__ = "1.0.0"
__author__ = "Jr Dev Agent Team"
__description__ = "LangGraph MCP Server for Jr Dev Agent"

# Package imports
from .utils.load_ticket_metadata import (
    load_ticket_metadata,
    load_from_fallback,
    validate_ticket_metadata,
    get_fallback_status,
    JiraMetadata,
    JiraFallbackError,
    JiraAPIError
)

from .nodes.jira_prompt_node import (
    JiraPromptNode,
    jira_prompt_node,
    create_jira_prompt_graph,
    get_jira_node_status
)

__all__ = [
    # Utils
    "load_ticket_metadata",
    "load_from_fallback", 
    "validate_ticket_metadata",
    "get_fallback_status",
    "JiraMetadata",
    "JiraFallbackError",
    "JiraAPIError",
    # Nodes
    "JiraPromptNode",
    "jira_prompt_node",
    "create_jira_prompt_graph",
    "get_jira_node_status"
] 