
import pytest
from fastapi.testclient import TestClient
from jr_dev_agent.server.main import app, add_mcp_routes, jr_dev_graph, session_manager

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_mcp_endpoint_registered(client: TestClient):
    """
    Verify the /mcp endpoint is registered in the application routes.
    Avoids making a request that might hang due to infinite SSE stream.
    """
    # Ensure routes are added (handled by startup event usually, but we can check or add)
    # In TestClient with Starlette/FastAPI, startup events run. 
    # We can also just inspect app.routes directly.
    
    routes = [route for route in app.routes]
    
    # Check if /mcp exists
    mcp_route_exists = any(
        getattr(route, "path", "") == "/mcp" and "GET" in getattr(route, "methods", [])
        for route in routes
    )
    assert mcp_route_exists, "/mcp endpoint not found in app routes"

def test_sse_endpoint_removed(client: TestClient):
    """
    Verify the old /sse endpoint is NOT registered.
    """
    routes = [route for route in app.routes]
    sse_route_exists = any(
        getattr(route, "path", "") == "/sse" 
        for route in routes
    )
    assert not sse_route_exists, "Found legacy /sse endpoint in app routes"

def test_root_mcp_discovery(client: TestClient):
    """
    Verify the root discovery endpoint returns the correct mcp endpoint path.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    
    assert "endpoints" in data
    assert "mcp" in data["endpoints"]
    assert data["endpoints"]["mcp"] == "GET /mcp"
    
    # Ensure we didn't leave the old key
    assert "sse" not in data["endpoints"]