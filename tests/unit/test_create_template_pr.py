import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from jr_dev_agent.server.main import app

client = TestClient(app)

@pytest.fixture
def mock_config():
    with patch("jr_dev_agent.tools.create_template_pr._load_config") as mock:
        mock.return_value = {
            "repository_url": "https://github.com/org/repo",
            "auth_token": "token"
        }
        yield mock

@pytest.fixture
def mock_httpx():
    with patch("httpx.AsyncClient", autospec=True) as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance

def test_create_template_pr_success(mock_config, mock_httpx):
    """Test successful PR creation flow"""
    # Initialize routes for test app
    from jr_dev_agent.server.mcp_gateway import add_mcp_routes
    from jr_dev_agent.server.main import jr_dev_graph, session_manager
    add_mcp_routes(app, jr_dev_graph, session_manager)

    # Setup mock responses for GitHub API chain
    
    async def side_effect(url, **kwargs):
        if "/git/ref/heads/main" in url:
            return MagicMock(status_code=200, json=lambda: {"object": {"sha": "main_sha_123"}})
        if "/contents/" in url:
            return MagicMock(status_code=200, json=lambda: {"sha": "old_file_sha_456"}) # File exists
        return MagicMock(status_code=404)

    mock_httpx.get.side_effect = side_effect
    
    async def post_side_effect(url, **kwargs):
        if "/git/refs" in url:
             return MagicMock(status_code=201)
        if "/pulls" in url:
             return MagicMock(status_code=201, json=lambda: {"html_url": "https://github.com/org/repo/pull/1"})
        return MagicMock(status_code=400)

    mock_httpx.post.side_effect = post_side_effect
    
    async def put_return(*args, **kwargs):
        return MagicMock(status_code=200)
    
    mock_httpx.put.side_effect = put_return

    # Execute MCP Request
    request_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_template_pr",
            "arguments": {
                "template_name": "feature",
                "updated_content": "name: feature\nnew_field: value",
                "pr_title": "Fix feature template",
                "pr_description": "Updated based on PESS score"
            }
        },
        "id": "test-1"
    }

    response = client.post("/mcp/tools/call", json=request_payload)
    
    # Assertions
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "result" in data, f"Response missing result: {data}"
    
    # Check for success
    if data["result"].get("isError"):
        pytest.fail(f"Tool returned error: {data['result']['content'][0]['text']}")
        
    assert data["result"]["_meta"]["status"] == "success"
    assert data["result"]["_meta"]["pr_url"] == "https://github.com/org/repo/pull/1"

def test_create_template_pr_invalid_template(mock_config):
    """Test error when template name is unknown"""
    # Initialize routes
    from jr_dev_agent.server.mcp_gateway import add_mcp_routes
    from jr_dev_agent.server.main import jr_dev_graph, session_manager
    add_mcp_routes(app, jr_dev_graph, session_manager)

    request_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_template_pr",
            "arguments": {
                "template_name": "unknown_template",
                "updated_content": "content",
                "pr_title": "title",
                "pr_description": "desc"
            }
        },
        "id": "test-2"
    }

    response = client.post("/mcp/tools/call", json=request_payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "result" in data
    assert data["result"]["isError"] is True
    assert "Unknown template name" in data["result"]["content"][0]["text"]

def test_create_template_pr_missing_config():
    """Test error when config is missing"""
    # Initialize routes
    from jr_dev_agent.server.mcp_gateway import add_mcp_routes
    from jr_dev_agent.server.main import jr_dev_graph, session_manager
    add_mcp_routes(app, jr_dev_graph, session_manager)

    with patch("jr_dev_agent.tools.create_template_pr._load_config", return_value=None):
        request_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "create_template_pr",
                "arguments": {
                    "template_name": "feature",
                    "updated_content": "content",
                    "pr_title": "title",
                    "pr_description": "desc"
                }
            },
            "id": "test-3"
        }

        response = client.post("/mcp/tools/call", json=request_payload)
        data = response.json()
        
        # Check for error in either top-level or result
        if "error" in data:
             assert "Configuration not found" in str(data["error"])
        elif "result" in data:
             if data["result"].get("isError"):
                 assert "Configuration not found" in data["result"]["content"][0]["text"]
             elif data["result"].get("content"):
                 assert "Configuration not found" in data["result"]["content"][0]["text"]
             else:
                 pytest.fail(f"Unexpected success structure: {data}")
        else:
             pytest.fail(f"Unexpected response structure: {data}")
