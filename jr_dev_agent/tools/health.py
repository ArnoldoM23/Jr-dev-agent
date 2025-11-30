import logging
from datetime import datetime
from typing import Dict, Any

from jr_dev_agent.models.mcp import HealthToolResult

logger = logging.getLogger(__name__)

async def handle_health_tool(jr_dev_graph, session_manager) -> Dict[str, Any]:
    """
    Handle health tool - check system status
    
    Reuses existing health check logic while providing MCP-formatted response.
    """
    logger.info("Health check requested via MCP")
    
    # Get health status from existing components
    graph_health = jr_dev_graph.get_health_status()
    session_stats = session_manager.get_stats()
    
    # Determine overall status
    overall_status = "healthy"
    
    # Count available tools from registry (imported dynamically to avoid circular import)
    # For now we assume the standard 3 tools
    mcp_tools_available = 3
    
    services = {
        "langgraph": "available" if graph_health.get("status") == "healthy" else "degraded",
        "session_manager": "available",
        "fallback_system": "available",
        "mcp_gateway": "available"
    }
    
    if "degraded" in services.values() or "unavailable" in services.values():
        overall_status = "degraded"
    
    result = HealthToolResult(
        status=overall_status,
        services=services,
        timestamp=datetime.now().isoformat(),
        mcp_tools_available=mcp_tools_available
    )
    
    return result.model_dump()

