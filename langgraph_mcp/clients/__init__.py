"""
Client helpers for external MCP services (Jira, Confluence, etc.).

These are intentionally thin wrappers so that the rest of the codebase can
operate the same way in both mock/offline development and in the enterprise
environment where the real MCP servers live.
"""

from .jira_client import JiraMCPClient
from .confluence_client import ConfluenceMCPClient

__all__ = ["JiraMCPClient", "ConfluenceMCPClient"]
