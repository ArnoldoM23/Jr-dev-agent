"""
MCP Jira Client
---------------

This module encapsulates the HTTP calls required to talk to the enterprise
Jira MCP server.  It gracefully falls back to the local development dataset
when real credentials are not available so the rest of the application can
continue to function in mock mode.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import requests


class JiraMCPClient:
    """Lightweight wrapper around the Jira MCP HTTP interface."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 10,
    ):
        self.logger = logging.getLogger(__name__)
        self.base_url = (base_url or os.getenv("JIRA_MCP_URL") or "").rstrip("/")
        self.token = token or os.getenv("JIRA_MCP_TOKEN") or os.getenv("PINGFED_TOKEN")
        self.timeout = timeout

    # ------------------------------------------------------------------ utils
    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ------------------------------------------------------------------ public
    def fetch_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch ticket details from the MCP server.

        Raises:
            RuntimeError: when the MCP call fails or returns malformed data.
        """
        if not self.configured:
            raise RuntimeError("Jira MCP client is not configured with URL/token")

        payload = {
            "jsonrpc": "2.0",
            "id": f"jrdev-fetch-{ticket_id}",
            "method": "tools/call",
            "params": {
                "name": "get_ticket",  # convention used by internal MCP
                "arguments": {"ticket_id": ticket_id},
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/tools/call",
                headers=self._headers(),
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to call Jira MCP: {exc!s}") from exc

        result = body.get("result") if isinstance(body, dict) else None
        if not result:
            raise RuntimeError(f"Jira MCP response missing result: {body}")

        ticket = result.get("ticket") or result.get("data") or result.get("metadata")
        if not ticket:
            raise RuntimeError(f"Jira MCP response missing ticket payload: {body}")

        return ticket
