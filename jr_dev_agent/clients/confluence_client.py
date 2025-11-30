"""
MCP Confluence Client
---------------------

Handles interactions with the enterprise Confluence MCP server while also
providing a mock-friendly path for local development.  The main use case for
the Jr Dev Agent is to update specification templates after a session has
been scored by PESS.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class ConfluenceMCPClient:
    """Wrapper around the Confluence MCP endpoint with local mock fallback."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 10,
        mock_storage_dir: Optional[Path] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.base_url = (base_url or os.getenv("CONFLUENCE_MCP_URL") or "").rstrip("/")
        self.token = token or os.getenv("CONFLUENCE_MCP_TOKEN") or os.getenv("PINGFED_TOKEN")
        self.timeout = timeout
        self.mock_storage_dir = mock_storage_dir or Path("syntheticMemory") / "_confluence_updates"

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
    def update_template(
        self,
        page_id: str,
        new_body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update the Confluence template body.

        When the client is not configured it writes the payload to a local file
        so we can inspect the would-be update during development.
        """
        if not self.configured:
            self.logger.info(
                "Confluence MCP not configured – writing update to mock directory",
                extra={"page_id": page_id},
            )
            self.mock_storage_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.mock_storage_dir / f"{page_id}.json"
            payload = {"page_id": page_id, "body": new_body, "metadata": metadata or {}}
            output_path.write_text(json.dumps(payload, indent=2))
            return {"status": "mock", "path": str(output_path)}

        payload = {
            "jsonrpc": "2.0",
            "id": f"jrdev-confluence-{page_id}",
            "method": "tools/call",
            "params": {
                "name": "update_template",
                "arguments": {
                    "page_id": page_id,
                    "body": new_body,
                    "metadata": metadata or {},
                },
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
            return response.json().get("result", {})
        except Exception as exc:
            raise RuntimeError(f"Failed to call Confluence MCP: {exc!s}") from exc
