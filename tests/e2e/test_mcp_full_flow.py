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
        # Mock ChatOpenAI
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
             patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
            
            # Setup mock LLM response
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Implement E2E API test changes."
            
            async def async_response(*args, **kwargs):
                return mock_response
            
            mock_llm.ainvoke.side_effect = async_response
            MockChatOpenAI.return_value = mock_llm
            
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
                    
                # 2. Finalize Session
                changes_made = "Implemented API test case."
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
                
                # Check summary.json
                summary_file = ticket_dir / "summary.json"
                assert summary_file.exists()
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
                
                assert summary_data.get("change_required") == "Implement E2E API test changes."
                assert summary_data.get("changes_made") == changes_made
                assert summary_data.get("pr_url") == pr_url
                
                # Check agent_run.json
                agent_run_file = ticket_dir / "agent_run.json"
                assert agent_run_file.exists()
                with open(agent_run_file, 'r') as f:
                    agent_run_data = json.load(f)
                
                assert agent_run_data.get("full_prompt") is not None
                assert agent_run_data.get("pr_url") == pr_url

    finally:
        # Restore root and cleanup
        jr_dev_graph.synthetic_memory.root = original_root
        if mem_root.exists():
            shutil.rmtree(mem_root)

@pytest.mark.asyncio
async def test_api_fallback_scenarios():
    """Test fallback logic for summary generation and memory persistence"""
    
    # Setup temp memory
    mem_root = Path("temp_fallback_memory")
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    # Override memory root
    original_root = jr_dev_graph.synthetic_memory.root
    jr_dev_graph.synthetic_memory.root = str(mem_root)
    
    try:
        # Ensure OPENAI_API_KEY is NOT set to trigger fallback
        with patch.dict(os.environ, {}, clear=True):
            # We might need to keep some env vars if any libraries depend on them (e.g. PATH),
            # but usually clear=True removes everything. 
            # Safer to just remove OPENAI_API_KEY if it exists.
            pass
        
        # Explicitly patch os.getenv to return None for OPENAI_API_KEY
        # because the server might have loaded it already or cached it?
        # PromptBuilder checks os.getenv inside generate_task_summary.
        
        with patch("os.getenv", side_effect=lambda k, d=None: None if k == "OPENAI_API_KEY" else os.environ.get(k, d)):
            
            with TestClient(app) as client:
                ticket_id = "FALLBACK-123"
                session_id = "session_fallback_123"
                
                # 1. Prepare Agent Task (expect fallback summary)
                prepare_payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": "1",
                    "params": {
                        "name": "prepare_agent_task",
                        "arguments": {"ticket_id": ticket_id}
                    }
                }
                
                description = "This is a detailed description of the task." + (" long text" * 20)
                
                with patch("jr_dev_agent.utils.load_ticket_metadata.load_ticket_metadata") as mock_load:
                    mock_load.return_value = {
                        "ticket_id": ticket_id,
                        "summary": "Fallback Test",
                        "description": description,
                        "files_affected": ["api.py"],
                        "acceptance_criteria": ["It works"],
                        "template_name": "feature"
                    }
                    
                    response = client.post("/mcp/tools/call", json=prepare_payload)
                    assert response.status_code == 200
                
                # 2. Finalize Session (changes_made=None, but provide feedback)
                feedback_text = "This is the summary of changes from feedback."
                
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
                            "feedback": feedback_text
                            # changes_made is intentionally omitted/None
                        }
                    }
                }
                
                response = client.post("/mcp/tools/call", json=finalize_payload)
                assert response.status_code == 200
                
                # 3. Verify Fallback Results
                found_dirs = list(mem_root.glob(f"**/{ticket_id}"))
                assert len(found_dirs) > 0
                ticket_dir = found_dirs[0]
                
                summary_file = ticket_dir / "summary.json"
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
                
                # Verify Change Required Fallback
                # Should be "Summary: DescriptionSnippet..."
                expected_start = "Fallback Test: This is a detailed description"
                assert summary_data.get("change_required").startswith(expected_start)
                
                # Verify Changes Made Fallback (from feedback)
                assert summary_data.get("changes_made") == feedback_text

    finally:
        jr_dev_graph.synthetic_memory.root = original_root
        if mem_root.exists():
            shutil.rmtree(mem_root)
