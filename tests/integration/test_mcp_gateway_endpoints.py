import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Force fallback mode so Jira MCP calls are not attempted during tests.
os.environ.setdefault("DEV_MODE", "true")

from langgraph_mcp.server.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_tools_list(client: TestClient):
    payload = {"jsonrpc": "2.0", "method": "tools/list", "id": "test-tools"}
    response = client.post("/mcp/tools/list", json=payload)
    assert response.status_code == 200
    body = response.json()
    tool_names = [tool["name"] for tool in body["result"]["tools"]]
    assert "prepare_agent_task" in tool_names
    assert "finalize_session" in tool_names


def test_prepare_and_finalize_flow(client: TestClient, monkeypatch):
    # Ensure Confluence mock writes to a temporary directory for the test.
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("CONFLUENCE_MCP_URL", "")

    ticket_id = "CEPG-67890"

    prepare_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": "prepare",
        "params": {"name": "prepare_agent_task", "arguments": {"ticket_id": ticket_id}},
    }
    prepare_response = client.post("/mcp/tools/call", json=prepare_payload)
    assert prepare_response.status_code == 200
    prepare_body = prepare_response.json()["result"]
    
    # Handle v2 structure (content + _meta)
    if "_meta" in prepare_body:
        metadata = prepare_body["_meta"]["metadata"]
        files_to_modify = metadata["files_to_modify"]
    else:
        # Fallback for v1 structure
        metadata = prepare_body["metadata"]
        files_to_modify = metadata["files_to_modify"]
        
    assert metadata["ticket_id"] == ticket_id

    finalize_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": "finalize",
        "params": {
            "name": "finalize_session",
            "arguments": {
                "session_id": "test-session",
                "ticket_id": ticket_id,
                "files_modified": files_to_modify,
                "duration_ms": 1000,
                "feedback": "Automated test feedback",
                "agent_telemetry": {"retries": 0},
            },
        },
    }
    finalize_response = client.post("/mcp/tools/call", json=finalize_payload)
    assert finalize_response.status_code == 200
    finalize_body = finalize_response.json()["result"]
    
    assert "_meta" in finalize_body
    assert finalize_body["_meta"]["pess_score"] >= 0.0

    # Verify that a Confluence payload was produced.
    confluence_path = Path("syntheticMemory") / "_confluence_updates" / f"{ticket_id}.json"
    assert confluence_path.exists()
    with confluence_path.open("r") as fh:
        payload = json.load(fh)
    assert payload["metadata"]["ticket_id"] == ticket_id
    # Clean up after assertions so repo stays pristine.
    confluence_path.unlink(missing_ok=True)
