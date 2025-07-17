"""
PromptBuilder Service API

FastAPI server for the PromptBuilder microservice.
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import uvicorn
from contextlib import asynccontextmanager

from ..service import promptbuilder


# Pydantic models for API
class PromptGenerationRequest(BaseModel):
    template_name: str
    ticket_data: Dict[str, Any]
    enrichment_data: Optional[Dict[str, Any]] = None


class PromptGenerationResponse(BaseModel):
    prompt: str
    template_used: str
    ticket_id: str
    generated_at: str
    success: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    initialized: bool


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await promptbuilder.initialize()
    yield
    # Shutdown
    await promptbuilder.cleanup()


# Create FastAPI app
app = FastAPI(
    title="PromptBuilder Service",
    description="AI-optimized prompt generation service for GitHub Copilot",
    version="1.0.0",
    lifespan=lifespan
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    status = promptbuilder.get_status()
    return HealthResponse(
        status="healthy" if status["initialized"] else "initializing",
        service=status["service"],
        version=status["version"],
        initialized=status["initialized"]
    )


@app.post("/generate", response_model=PromptGenerationResponse)
async def generate_prompt(request: PromptGenerationRequest):
    """Generate an AI-optimized prompt"""
    try:
        if not promptbuilder.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Generate the prompt
        prompt = await promptbuilder.generate_prompt(
            template_name=request.template_name,
            ticket_data=request.ticket_data,
            enrichment_data=request.enrichment_data
        )
        
        from datetime import datetime
        
        return PromptGenerationResponse(
            prompt=prompt,
            template_used=request.template_name,
            ticket_id=request.ticket_data.get("ticket_id", "unknown"),
            generated_at=datetime.now().isoformat(),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")


@app.get("/templates")
async def get_supported_templates():
    """Get list of supported templates"""
    return {
        "templates": ["feature", "bugfix", "refactor"],
        "service": "PromptBuilder",
        "version": "1.0.0"
    }


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    return promptbuilder.get_status()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 