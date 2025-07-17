"""
Session Management Service API

FastAPI server for the Session Management microservice.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import uvicorn
from contextlib import asynccontextmanager

from ..service import session_manager, SessionStatus


# Pydantic models for API
class CreateSessionRequest(BaseModel):
    ticket_id: str
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    session_id: str
    ticket_id: str
    status: str
    created_at: str


class UpdateSessionRequest(BaseModel):
    status: Optional[str] = None
    prompt_generated: Optional[str] = None
    prompt_hash: Optional[str] = None
    template_used: Optional[str] = None
    pr_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CompleteSessionRequest(BaseModel):
    pr_url: Optional[str] = None
    completed_at: Optional[str] = None


class FailSessionRequest(BaseModel):
    error_message: str


class SessionResponse(BaseModel):
    session_id: str
    ticket_id: str
    status: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    prompt_generated: Optional[str] = None
    prompt_hash: Optional[str] = None
    template_used: Optional[str] = None
    pr_url: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    initialized: bool
    total_sessions: int
    active_sessions: int


class SessionStatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    status_breakdown: Dict[str, int]
    session_timeout_minutes: float


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await session_manager.initialize()
    yield
    # Shutdown
    await session_manager.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Session Management Service",
    description="Session lifecycle management for Jr Dev Agent workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    status = session_manager.get_status()
    return HealthResponse(
        status="healthy" if status["initialized"] else "initializing",
        service=status["service"],
        version=status["version"],
        initialized=status["initialized"],
        total_sessions=status["total_sessions"],
        active_sessions=status["active_sessions"]
    )


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new session"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        session_id = session_manager.create_session(
            ticket_id=request.ticket_id,
            metadata=request.metadata
        )
        
        session = session_manager.get_session(session_id)
        
        return CreateSessionResponse(
            session_id=session_id,
            ticket_id=request.ticket_id,
            status=session.status.value,
            created_at=session.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a session by ID"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        return SessionResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@app.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """Update a session"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Convert status string to enum if provided
        updates = request.dict(exclude_none=True)
        if 'status' in updates:
            updates['status'] = SessionStatus(updates['status'])
        
        success = session_manager.update_session(session_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        session = session_manager.get_session(session_id)
        return SessionResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@app.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(session_id: str, request: CompleteSessionRequest):
    """Mark a session as completed"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        success = session_manager.complete_session(
            session_id=session_id,
            pr_url=request.pr_url,
            completed_at=request.completed_at
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        session = session_manager.get_session(session_id)
        return SessionResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete session: {str(e)}")


@app.post("/sessions/{session_id}/fail", response_model=SessionResponse)
async def fail_session(session_id: str, request: FailSessionRequest):
    """Mark a session as failed"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        success = session_manager.fail_session(
            session_id=session_id,
            error_message=request.error_message
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        session = session_manager.get_session(session_id)
        return SessionResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error failing session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fail session: {str(e)}")


@app.get("/tickets/{ticket_id}/sessions", response_model=List[SessionResponse])
async def get_sessions_by_ticket(ticket_id: str):
    """Get all sessions for a specific ticket"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        sessions = session_manager.get_sessions_by_ticket(ticket_id)
        return [SessionResponse(**session.to_dict()) for session in sessions]
        
    except Exception as e:
        logger.error(f"Error getting sessions for ticket {ticket_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@app.get("/sessions", response_model=List[SessionResponse])
async def get_all_sessions():
    """Get all sessions"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        sessions_data = session_manager.get_all_sessions()
        return [SessionResponse(**session_data) for session_data in sessions_data]
        
    except Exception as e:
        logger.error(f"Error getting all sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@app.get("/sessions/active", response_model=List[SessionResponse])
async def get_active_sessions():
    """Get all active sessions"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        sessions = session_manager.get_active_sessions()
        return [SessionResponse(**session.to_dict()) for session in sessions]
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get active sessions: {str(e)}")


@app.get("/stats", response_model=SessionStatsResponse)
async def get_session_stats():
    """Get session statistics"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        stats = session_manager.get_stats()
        return SessionStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting session stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/cleanup")
async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    try:
        if not session_manager.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        cleaned_count = session_manager.cleanup_expired_sessions()
        return {"cleaned_sessions": cleaned_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    return session_manager.get_status()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003) 