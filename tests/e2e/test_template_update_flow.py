import pytest
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from jr_dev_agent.server.main import app, jr_dev_graph

# Import route adder
from jr_dev_agent.server.mcp_gateway import add_mcp_routes
from jr_dev_agent.server.main import jr_dev_graph, session_manager

@pytest.fixture(autouse=True)
def ensure_routes():
    # Ensure MCP routes are registered for all tests in this file
    add_mcp_routes(app, jr_dev_graph, session_manager)

@pytest.mark.asyncio
async def test_template_update_e2e_flow():
    """
    Test the full workflow:
    1. Prepare task
    2. Finalize session with LOW PESS score -> trigger template update request
    3. Call create_template_pr tool -> creates PR
    """
    
    # Setup temp memory
    mem_root = Path("temp_template_e2e_memory")
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    # Override memory root
    original_root = jr_dev_graph.synthetic_memory.root
    jr_dev_graph.synthetic_memory.root = str(mem_root)
    
    # Mock config for create_template_pr
    with patch("jr_dev_agent.tools.create_template_pr._load_config") as mock_config:
        mock_config.return_value = {
            "repository_url": "https://github.com/ArnoldoM23/jr-dev-agent-prompt-templates",
            "auth_token": "mock_token"
        }
        
        # Mock httpx.AsyncClient for GitHub API calls
        with patch("httpx.AsyncClient", autospec=True) as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_client_instance
            
            # Setup successful GitHub interactions
            async def get_side_effect(url, **kwargs):
                if "/git/ref/heads/main" in url:
                    return MagicMock(status_code=200, json=lambda: {"object": {"sha": "main_sha_123"}})
                if "/contents/" in url:
                    return MagicMock(status_code=200, json=lambda: {"sha": "file_sha_456"})
                return MagicMock(status_code=404)
            
            mock_client_instance.get.side_effect = get_side_effect
            
            async def post_side_effect(url, **kwargs):
                if "/git/refs" in url: # Create branch
                     return MagicMock(status_code=201)
                if "/pulls" in url: # Create PR
                     return MagicMock(status_code=201, json=lambda: {"html_url": "https://github.com/test/pr/new"})
                return MagicMock(status_code=400)
            
            mock_client_instance.post.side_effect = post_side_effect
            
            async def put_return(*args, **kwargs):
                return MagicMock(status_code=200)
            mock_client_instance.put.side_effect = put_return

            try:
                with TestClient(app) as client:
                    ticket_id = "TEMPLATE-123"
                    
                    # 1. Prepare Agent Task
                    prepare_payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "id": "1",
                        "params": {
                            "name": "prepare_agent_task",
                            "arguments": {
                                "ticket_id": ticket_id
                            }
                        }
                    }
                    
                    with patch("jr_dev_agent.utils.load_ticket_metadata.load_ticket_metadata") as mock_load:
                        mock_load.return_value = {
                            "ticket_id": ticket_id,
                            "summary": "Template Update Test",
                            "description": "Testing template update flow",
                            "template_name": "feature",
                            "files_affected": []
                        }
                        
                        response = client.post("/mcp/tools/call", json=prepare_payload)
                        assert response.status_code == 200
                        result = response.json()["result"]
                        session_id = result["_meta"]["metadata"]["session_id"]
                        
                    # 2. Finalize Session with LOW SCORE (to trigger update request)
                    # We need to mock PESS service to return low score
                    # jr_dev_agent.tools.finalize_session uses pess_service.score_session_completion
                    
                    with patch("jr_dev_agent.services.pess_client.PESSClient.score_session_completion") as mock_score:
                        # Return score < 80.0
                        mock_score.return_value = {
                            "prompt_score": 0.65, # 65%
                            "score_percent": 65.0,
                            "clarity_rating": "Low",
                            "recommendation": "Poor quality prompt",
                            "mock_response": True
                        }
                        
                        finalize_payload = {
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "id": "2",
                            "params": {
                                "name": "finalize_session",
                                "arguments": {
                                    "session_id": session_id,
                                    "ticket_id": ticket_id,
                                    "pr_url": "https://github.com/test/pr/code",
                                    "files_modified": ["src/main.py"],
                                    "duration_ms": 1000,
                                    "change_required": "Code changes",
                                    "changes_made": "Done changes",
                                    "feedback": "Prompt was confusing"
                                }
                            }
                        }
                        
                        response = client.post("/mcp/tools/call", json=finalize_payload)
                        assert response.status_code == 200
                        result = response.json()["result"]
                        
                        # Verify PESS Score is low
                        assert result["_meta"]["pess_score"] == 65.0
                        
                        # Verify Template Update Request is present
                        update_req = result["_meta"].get("template_update_request")
                        assert update_req is not None
                        assert update_req["required"] is True
                        assert update_req["template_name"] == "feature"
                        assert "65.0" in update_req["reason"]
                        
                        # Verify the TEXT response tells the agent to update
                        content_text = result["content"][0]["text"]
                        assert "TEMPLATE UPDATE REQUIRED" in content_text
                        assert "create_template_pr" in content_text

                    # 3. Call create_template_pr (Simulating Agent action)
                    pr_payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "id": "3",
                        "params": {
                            "name": "create_template_pr",
                            "arguments": {
                                "template_name": "feature",
                                "updated_content": "name: feature\nnew_instruction: improve this",
                                "pr_title": "Improve feature template",
                                "pr_description": "Addressing low PESS score"
                            }
                        }
                    }
                    
                    response = client.post("/mcp/tools/call", json=pr_payload)
                    assert response.status_code == 200
                    result = response.json()["result"]
                    
                    # Verify PR creation success
                    assert result["_meta"]["status"] == "success"
                    assert result["_meta"]["pr_url"] == "https://github.com/test/pr/new"
                    assert "Successfully created PR" in result["content"][0]["text"]
            
            finally:
                # Cleanup
                jr_dev_graph.synthetic_memory.root = original_root
                if mem_root.exists():
                    shutil.rmtree(mem_root)
