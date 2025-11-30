"""
LangGraph MCP Server - Main FastAPI Application

This is the central orchestration server that handles requests from the VS Code extension
and coordinates the AI agent workflow using LangGraph.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from langgraph_mcp.graph.jr_dev_graph import JrDevGraph
from langgraph_mcp.utils.load_ticket_metadata import load_ticket_metadata
from langgraph_mcp.models.session import SessionManager
from langgraph_mcp.models.ticket import TicketMetadata
from langgraph_mcp.models.prompt import PromptRequest, PromptResponse
from langgraph_mcp.mcp_gateway import add_mcp_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Jr Dev Agent - Gateway MCP Server",
    description="AI-powered junior developer agent with cross-IDE support via MCP protocol",
    version="2.0.0-mvp",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
session_manager = SessionManager()
jr_dev_graph = JrDevGraph()

# Pydantic models for API requests/responses
class SessionCompleteRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to mark complete")
    pr_url: Optional[str] = Field(None, description="Optional PR URL")
    completed_at: str = Field(..., description="ISO timestamp of completion")

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    services: Dict[str, str] = Field(default_factory=dict)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {
        "langgraph": "available",
        "session_manager": "available",
        "fallback_system": "available"
    }
    
    return HealthResponse(services=services)

@app.get("/api/ticket/{ticket_id}")
async def get_ticket_metadata(ticket_id: str) -> Dict[str, Any]:
    """
    Get ticket metadata from Jira (with fallback support)
    
    This endpoint is called by the VS Code extension to fetch ticket information.
    It uses the existing fallback system if the MCP server is unavailable.
    """
    try:
        logger.info(f"Fetching ticket metadata for: {ticket_id}")
        
        # Use our existing fallback system
        ticket_data = load_ticket_metadata(ticket_id)
        
        # Convert to the format expected by the VS Code extension
        response = {
            "ticket_id": ticket_data["ticket_id"],
            "template_name": ticket_data.get("template_name", "feature"),
            "summary": ticket_data["summary"],
            "description": ticket_data["description"],
            "acceptance_criteria": ticket_data.get("acceptance_criteria", []),
            "files_affected": ticket_data.get("files_affected", []),
            "feature": ticket_data.get("feature", "unknown"),
            "priority": ticket_data.get("priority", "Medium"),
            "assignee": ticket_data.get("assignee", "unassigned"),
            "labels": ticket_data.get("labels", []),
            "components": ticket_data.get("components", []),
            "source": "mcp"  # Mark as coming from MCP server
        }
        
        logger.info(f"Successfully fetched ticket metadata for {ticket_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching ticket metadata for {ticket_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ticket metadata: {str(e)}"
        )

@app.post("/api/prompt/generate")
async def generate_prompt(request: PromptRequest) -> PromptResponse:
    """
    Generate AI-optimized prompt using LangGraph
    
    This endpoint processes ticket data through the LangGraph workflow
    to generate an optimized prompt for GitHub Copilot.
    """
    try:
        logger.info(f"Generating prompt for ticket: {request.ticket_data.ticket_id}")
        
        # Create a session for this request
        session_id = session_manager.create_session(
            ticket_id=request.ticket_data.ticket_id,
            metadata={"source": "api_prompt_generate"}
        )
        
        # Process through LangGraph
        result = await jr_dev_graph.process_ticket(
            ticket_data=request.ticket_data.model_dump(),
            session_id=session_id
        )
        
        # Create response
        response = PromptResponse(
            prompt=result["prompt"],
            hash=result["hash"],
            template_used=result["template_used"],
            generated_at=datetime.now().isoformat(),
            metadata=request.ticket_data
        )
        
        logger.info(f"Successfully generated prompt for {request.ticket_data.ticket_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate prompt: {str(e)}"
        )

@app.post("/api/session/complete")
async def mark_session_complete(
    request: SessionCompleteRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Mark a session as complete and trigger analytics
    
    This endpoint is called when a developer marks their PR as complete.
    It triggers background processing for PESS scoring and analytics.
    """
    try:
        logger.info(f"Marking session complete: {request.session_id}")
        
        # Update session status
        session_manager.complete_session(
            session_id=request.session_id,
            pr_url=request.pr_url,
            completed_at=request.completed_at
        )
        
        # Queue background tasks for analytics
        background_tasks.add_task(
            process_session_completion,
            request.session_id,
            request.pr_url
        )
        
        logger.info(f"Successfully marked session complete: {request.session_id}")
        return {"status": "success", "message": "Session marked complete"}
        
    except Exception as e:
        logger.error(f"Error marking session complete: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark session complete: {str(e)}"
        )

# Background task functions
async def process_session_completion(session_id: str, pr_url: Optional[str]):
    """
    Background task to process session completion
    
    This will eventually trigger:
    - PESS scoring
    - Synthetic memory updates
    - Analytics collection
    """
    try:
        logger.info(f"Processing session completion: {session_id}")
        
        # Placeholder for future PESS integration
        # await pess_service.score_session(session_id)
        
        # Placeholder for future Synthetic Memory integration
        # await synthetic_memory.update_session_context(session_id, pr_url)
        
        logger.info(f"Session completion processing finished: {session_id}")
        
    except Exception as e:
        logger.error(f"Error processing session completion: {str(e)}")

# Development endpoints
@app.get("/api/debug/sessions")
async def get_debug_sessions():
    """Debug endpoint to view active sessions"""
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=404, detail="Not found")
    
    return session_manager.get_all_sessions()

@app.get("/api/debug/health")
async def get_debug_health():
    """Debug endpoint for detailed health information"""
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=404, detail="Not found")
    
    return {
        "langgraph": jr_dev_graph.get_health_status(),
        "session_manager": session_manager.get_stats(),
        "environment": {
            "dev_mode": os.getenv("DEV_MODE", "false"),
            "python_version": os.sys.version,
            "working_directory": os.getcwd()
        }
    }

# v2 functionality now integrated into enhanced LangGraph workflow
# Available through MCP Gateway with Synthetic Memory and PESS integration

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Jr Dev Agent MCP Server starting up...")
    
    # Initialize LangGraph
    await jr_dev_graph.initialize()
    
    # Initialize session manager
    session_manager.initialize()
    
    # Add MCP Gateway routes (enhanced with v2 Synthetic Memory & PESS integration)
    add_mcp_routes(app, jr_dev_graph, session_manager)
    logger.info("✅ MCP Gateway routes added with v2 enhancements (Synthetic Memory + PESS)")
    
    logger.info("✅ Jr Dev Agent MCP Server ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Jr Dev Agent MCP Server shutting down...")
    
    # Cleanup services
    await jr_dev_graph.cleanup()
    session_manager.cleanup()
    
    logger.info("✅ Jr Dev Agent MCP Server shutdown complete")

# Main entry point
if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    logger.info(f"Starting Jr Dev Agent MCP Server on {host}:{port}")
    logger.info(f"Development mode: {dev_mode}")
    
    uvicorn.run(
        "langgraph_mcp.server.main:app",
        host=host,
        port=port,
        reload=dev_mode,
        log_level="info"
    ) 