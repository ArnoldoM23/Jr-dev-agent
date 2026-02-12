import logging
from datetime import datetime
from typing import Dict, Any

from jr_dev_agent.models.mcp import HealthToolResult, HealthServiceInfo

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
        "langgraph": HealthServiceInfo(
            status="available" if graph_health.get("status") == "healthy" else "degraded",
            version="langgraph",
            details={
                "graph_initialized": graph_health.get("graph_initialized", False),
                "components": {
                    "prompt_builder": graph_health.get("prompt_builder", {}),
                    "template_engine": graph_health.get("template_engine", {}),
                    "jira_prompt_node": graph_health.get("jira_prompt_node", {}),
                    "synthetic_memory": graph_health.get("synthetic_memory", {}),
                    "pess_client": graph_health.get("pess_client", {}),
                    "prompt_composer": graph_health.get("prompt_composer", {}),
                },
            },
        ),
        "session_manager": HealthServiceInfo(
            status="available",
            version="session_manager",
            details={"stats": session_stats},
        ),
        "fallback_system": HealthServiceInfo(
            status="available",
            version="fallback",
            details={},
        ),
        "mcp_gateway": HealthServiceInfo(
            status="available",
            version="mcp_gateway",
            details={},
        ),
    }
    
    service_statuses = [svc.status for svc in services.values()]
    if "degraded" in service_statuses or "unavailable" in service_statuses:
        overall_status = "degraded"
    
    result = HealthToolResult(
        status=overall_status,
        services=services,
        timestamp=datetime.now().isoformat(),
        mcp_tools_available=mcp_tools_available
    )
    
    return result.model_dump()

