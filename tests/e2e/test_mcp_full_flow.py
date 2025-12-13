import pytest
import os
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from jr_dev_agent.server.main import app, jr_dev_graph, session_manager

@pytest.mark.asyncio
async def test_api_e2e_flow():
    """Test full E2E flow via API endpoints"""
    
    # Setup temp memory
    mem_root = Path("temp_e2e_memory")
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    # Override memory root by patching the global instance
    # jr_dev_graph is already initialized in jr_dev_agent.server.main
    original_root = jr_dev_graph.synthetic_memory.root
    jr_dev_graph.synthetic_memory.root = str(mem_root)
    
    try:
        # Use TestClient as context manager to trigger startup/shutdown
        with TestClient(app) as client:
            
            ticket_id = "CEPG-12345"
            session_id = "session_cepg_12345"
            
            # 1. Prepare Agent Task
            prepare_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "1",
                "params": {
                    "name": "prepare_agent_task",
                    "arguments": {
                        "ticket_id": ticket_id
                        # Don't pass project_root so it uses the global (patched) synthetic_memory
                    }
                }
            }
            
            # Mock load_ticket_metadata globally
            with patch("jr_dev_agent.utils.load_ticket_metadata.load_ticket_metadata") as mock_load:
                mock_load.return_value = {
                    "ticket_id": ticket_id,
                    "summary": "E2E API Test",
                    "description": "Testing the API flow",
                    "files_affected": ["api.py"],
                    "acceptance_criteria": ["It works"],
                    "template_name": "feature"
                }
                
                response = client.post("/mcp/tools/call", json=prepare_payload)
                assert response.status_code == 200
                if "error" in response.json():
                    pytest.fail(f"Tool call failed: {response.json()['error']}")
                
                result = response.json()["result"]
                
                # Verify content
                assert "content" in result
                assert len(result["content"]) > 0
                assert "prompt_text" in result["_meta"]
                
            # 2. Finalize Session (agent provides both summaries)
            change_required = "Add E2E API testing capability."
            changes_made = "Implemented API test case with mocked responses."
            pr_url = "https://github.com/test/pr/1"
            
            finalize_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "2",
                "params": {
                    "name": "finalize_session",
                    "arguments": {
                        "session_id": session_id,
                        "ticket_id": ticket_id,
                        "pr_url": pr_url,
                        "files_modified": ["api.py"],
                        "duration_ms": 500,
                        "change_required": change_required,
                        "changes_made": changes_made
                    }
                }
            }
            
            response = client.post("/mcp/tools/call", json=finalize_payload)
            assert response.status_code == 200
            if "error" in response.json():
                pytest.fail(f"Finalize call failed: {response.json()['error']}")
            
            # 3. Verify Memory Files
            # Let's search for the directory
            found_dirs = list(mem_root.glob(f"**/{ticket_id}"))
            assert len(found_dirs) > 0
            ticket_dir = found_dirs[0]
            
            # summary.json should NOT exist
            summary_file = ticket_dir / "summary.json"
            assert not summary_file.exists(), "summary.json should be deleted"
            
            # Check agent_run.json
            agent_run_file = ticket_dir / "agent_run.json"
            assert agent_run_file.exists()
            with open(agent_run_file, 'r') as f:
                agent_run_data = json.load(f)
            
            assert agent_run_data.get("full_prompt") is not None
            assert agent_run_data.get("pr_url") == pr_url
            assert agent_run_data.get("change_required") == change_required
            assert agent_run_data.get("changes_made") == changes_made
            assert "created_at" in agent_run_data

    finally:
        # Restore root and cleanup
        jr_dev_graph.synthetic_memory.root = original_root
        if mem_root.exists():
            shutil.rmtree(mem_root)

@pytest.mark.asyncio
async def test_api_fallback_scenarios():
    """Test fallback logic when summaries are not provided"""
    
    # Setup temp memory
    mem_root = Path("temp_fallback_memory")
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    # Override memory root
    original_root = jr_dev_graph.synthetic_memory.root
    jr_dev_graph.synthetic_memory.root = str(mem_root)
    
    try:
        with TestClient(app) as client:
            ticket_id = "FALLBACK-123"
            session_id = "session_fallback_123"
            
            # 1. Prepare Agent Task
            prepare_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "1",
                "params": {
                    "name": "prepare_agent_task",
                    "arguments": {"ticket_id": ticket_id}
                }
            }
            
            with patch("jr_dev_agent.utils.load_ticket_metadata.load_ticket_metadata") as mock_load:
                mock_load.return_value = {
                    "ticket_id": ticket_id,
                    "summary": "Fallback Test",
                    "description": "Testing fallback scenarios",
                    "files_affected": ["api.py"],
                    "acceptance_criteria": ["It works"],
                    "template_name": "feature"
                }
                
                response = client.post("/mcp/tools/call", json=prepare_payload)
                assert response.status_code == 200
            
            # 2. Finalize Session with NO change_required/changes_made -> Should Fail validation
            
            finalize_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "2",
                "params": {
                    "name": "finalize_session",
                    "arguments": {
                        "session_id": session_id,
                        "ticket_id": ticket_id,
                        "pr_url": "https://github.com/test/pr/fallback",
                        "files_modified": ["api.py"],
                        "duration_ms": 100,
                        "feedback": "Feedback provided."
                        # Both change_required and changes_made intentionally omitted
                    }
                }
            }
            
            # This should now return an error because fields are required
            response = client.post("/mcp/tools/call", json=finalize_payload)
            # The MCP server might return 200 OK but with an error inside the JSON-RPC response
            # OR FastAPI validation error (422 Unprocessable Entity) depending on implementation.
            # But since it's wrapped in MCP tool execution, it might be an MCP error.
            # However, tool arguments validation happens at Pydantic level.
            
            # If arguments don't match schema, mcp_gateway.py catches ValidationError
            # and returns an error response.
            
            assert response.status_code == 200
            response_json = response.json()
            assert "error" in response_json
            assert response_json["error"]["code"] == -32602 # Invalid params
            
            # 3. Success Path (Retry with correct params)
            change_required = "Req summary"
            changes_made = "Changes summary"
            
            finalize_payload["params"]["arguments"]["change_required"] = change_required
            finalize_payload["params"]["arguments"]["changes_made"] = changes_made
            
            response = client.post("/mcp/tools/call", json=finalize_payload)
            assert response.status_code == 200
            assert "result" in response.json()

    finally:
        jr_dev_graph.synthetic_memory.root = original_root
        if mem_root.exists():
            shutil.rmtree(mem_root)

@pytest.mark.asyncio
async def test_api_custom_project_root():
    """Test full E2E flow with a custom project root"""
    
    # Setup custom project root
    custom_root = Path("temp_custom_project")
    if custom_root.exists():
        shutil.rmtree(custom_root)
    custom_root.mkdir()
    
    # We DO NOT patch jr_dev_graph.synthetic_memory.root here
    # We want to ensure it uses the custom_root passed in args
    
    try:
        with TestClient(app) as client:
            
            ticket_id = "CUSTOM-123"
            session_id = "session_custom_123"
            
            # 1. Prepare Agent Task with project_root
            prepare_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "1",
                "params": {
                    "name": "prepare_agent_task",
                    "arguments": {
                        "ticket_id": ticket_id,
                        "project_root": str(custom_root.absolute())
                    }
                }
            }
            
            with patch("jr_dev_agent.utils.load_ticket_metadata.load_ticket_metadata") as mock_load:
                mock_load.return_value = {
                    "ticket_id": ticket_id,
                    "summary": "Custom Root Test",
                    "description": "Testing custom project root",
                    "files_affected": ["api.py"],
                    "acceptance_criteria": ["It works"],
                    "template_name": "feature"
                }
                
                response = client.post("/mcp/tools/call", json=prepare_payload)
                assert response.status_code == 200
                
                # Get session_id from prepare result
                result = response.json()["result"]
                session_id = result["_meta"]["metadata"]["session_id"]
                
            # 2. Finalize Session
            changes_made = "Implemented custom root support."
            change_required = "Implement custom root."
            
            finalize_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "2",
                "params": {
                    "name": "finalize_session",
                    "arguments": {
                        "session_id": session_id,
                        "ticket_id": ticket_id,
                        "pr_url": "",
                        "files_modified": [],
                        "duration_ms": 100,
                        "changes_made": changes_made,
                        "change_required": change_required
                    }
                }
            }
            
            response = client.post("/mcp/tools/call", json=finalize_payload)
            assert response.status_code == 200
            
            # 3. Verify Memory Files in CUSTOM ROOT
            # Should be in custom_root/syntheticMemory
            memory_dir = custom_root / "syntheticMemory"
            assert memory_dir.exists(), "Memory directory not created in custom root"
            
            found_dirs = list(memory_dir.glob(f"**/{ticket_id}"))
            assert len(found_dirs) > 0, "Ticket directory not found in custom root"
            ticket_dir = found_dirs[0]
            
            # summary.json should NOT exist
            summary_file = ticket_dir / "summary.json"
            assert not summary_file.exists(), "summary.json should be deleted"
            
            # agent_run.json
            agent_run_file = ticket_dir / "agent_run.json"
            assert agent_run_file.exists()
            with open(agent_run_file, 'r') as f:
                agent_run_data = json.load(f)
            
            # Verify data
            assert agent_run_data.get("changes_made") == changes_made
            assert "created_at" in agent_run_data
            
            # Verify NOT in default location (jr_dev_agent root)
            # But the test environment might be dirty or use real syntheticMemory.
            # We can't easily check "not in default" if default is the repo root which might have it from other runs.
            # But verifying it IS in custom root is the key success criteria.

    finally:
        if custom_root.exists():
            shutil.rmtree(custom_root)
