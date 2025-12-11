#!/usr/bin/env python3
"""
Demo helper for the Jr Dev Agent MCP workflow.

Usage:
    python scripts/demo_mcp_workflow.py --ticket CEPG-67890

The script assumes the MCP server is already running locally
(python scripts/start_mcp_gateway.py) and exercises the three
primary MCP tools:
    1. tools/list
    2. prepare_agent_task
    3. finalize_session

This is designed for local demos where the enterprise Jira/Confluence
MCP servers are not accessible. Responses are printed in a readable form
so the workflow can be showcased end-to-end.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from typing import Any, Dict

import requests

MCP_URL = "http://127.0.0.1:8000"

def post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f"{MCP_URL}{endpoint}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

def print_section(title: str, content: str) -> None:
    bar = "=" * len(title)
    print(f"\n{title}\n{bar}\n{content}")

def main(ticket_id: str, session_id: str, project_root: str = None) -> None:
    # 1. List available tools
    tools_payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": "demo-tools",
    }
    tools_response = post("/mcp/tools/list", tools_payload)
    print_section("Tools", json.dumps(tools_response, indent=2))

    # 2. Prepare agent task
    params = {
        "name": "prepare_agent_task",
        "arguments": {"ticket_id": ticket_id},
    }
    if project_root:
        params["arguments"]["project_root"] = project_root

    prepare_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": "demo-prepare",
        "params": params,
    }
    prepare_response = post("/mcp/tools/call", prepare_payload)
    prompt_text = prepare_response.get("result", {}).get("prompt_text", "").replace("\\n", "\n")
    metadata = prepare_response.get("result", {}).get("metadata", {})
    print_section("Prepared Prompt (metadata)", json.dumps(metadata, indent=2))
    print_section("Prepared Prompt (text)", textwrap.shorten(prompt_text, width=800, placeholder="…"))

    # 3. Finalize session with demo feedback
    finalize_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": "demo-finalize",
        "params": {
            "name": "finalize_session",
            "arguments": {
                "session_id": session_id,
                "ticket_id": ticket_id,
                "files_modified": metadata.get("files_to_modify", []),
                "duration_ms": 5 * 60 * 1000,
                "feedback": "Demo run completed successfully",
                "change_required": "Add pickup option to Order schema with store selection.",
                "changes_made": "Updated GraphQL types and resolvers to support store pickup functionality.",
                "agent_telemetry": {"retries": 0},
            },
        },
    }
    finalize_response = post("/mcp/tools/call", finalize_payload)
    print_section("Finalize Session", json.dumps(finalize_response, indent=2))

    print("\nDemo complete. See syntheticMemory/_confluence_updates/ for the mock Confluence payload.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo Jr Dev Agent MCP workflow")
    parser.add_argument("--ticket", default="CEPG-67890", help="Ticket ID to process")
    parser.add_argument("--session", default="demo-session", help="Session ID to use for finalize step")
    parser.add_argument("--project-root", help="Path to project root for memory storage")
    args = parser.parse_args()
    main(ticket_id=args.ticket, session_id=args.session, project_root=args.project_root)