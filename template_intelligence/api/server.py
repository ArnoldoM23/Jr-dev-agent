"""
Template Intelligence Service API

FastAPI server for the Template Intelligence microservice.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import uvicorn
from contextlib import asynccontextmanager

from ..engine.template_engine import template_engine


# Pydantic models for API
class TemplateSelectionRequest(BaseModel):
    ticket_data: Dict[str, Any]


class TemplateSelectionResponse(BaseModel):
    selected_template: str
    confidence_score: float
    ticket_id: str
    suggestions: List[Dict[str, Any]]


class TemplateValidationRequest(BaseModel):
    template_name: str
    ticket_data: Dict[str, Any]


class TemplateValidationResponse(BaseModel):
    valid: bool
    missing_fields: List[str]
    optional_fields: List[str]
    template_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    initialized: bool
    total_templates: int
    template_names: List[str]


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await template_engine.initialize()
    yield
    # Shutdown
    await template_engine.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Template Intelligence Service",
    description="Intelligent template selection and management service",
    version="1.0.0",
    lifespan=lifespan
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    status = template_engine.get_status()
    return HealthResponse(
        status="healthy" if status["initialized"] else "initializing",
        service=status["service"],
        version=status["version"],
        initialized=status["initialized"],
        total_templates=status["total_templates"],
        template_names=status["template_names"]
    )


@app.post("/select", response_model=TemplateSelectionResponse)
async def select_template(request: TemplateSelectionRequest):
    """Select the best template for a ticket"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Select template
        selected_template = template_engine.select_template(request.ticket_data)
        
        # Get suggestions
        suggestions = template_engine.get_template_suggestions(request.ticket_data)
        
        # Calculate confidence score based on suggestions
        confidence_score = 0.8  # Default confidence
        if suggestions:
            top_score = suggestions[0].get('score', 0)
            if top_score > 0:
                confidence_score = min(0.95, 0.5 + (top_score / 10))
        
        return TemplateSelectionResponse(
            selected_template=selected_template,
            confidence_score=confidence_score,
            ticket_id=request.ticket_data.get("ticket_id", "unknown"),
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error selecting template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template selection failed: {str(e)}")


@app.post("/validate", response_model=TemplateValidationResponse)
async def validate_template(request: TemplateValidationRequest):
    """Validate ticket data against a template"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Validate template data
        validation_result = template_engine.validate_template_data(
            request.template_name, 
            request.ticket_data
        )
        
        return TemplateValidationResponse(**validation_result)
        
    except Exception as e:
        logger.error(f"Error validating template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template validation failed: {str(e)}")


@app.get("/templates")
async def get_all_templates():
    """Get all available templates"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        templates = template_engine.get_all_templates()
        return {
            "templates": templates,
            "total": len(templates),
            "categories": template_engine.get_template_categories()
        }
        
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@app.get("/templates/{template_name}")
async def get_template(template_name: str):
    """Get a specific template by name"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        template = template_engine.get_template(template_name)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@app.get("/categories")
async def get_template_categories():
    """Get all template categories"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        categories = template_engine.get_template_categories()
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@app.get("/categories/{category}")
async def get_templates_by_category(category: str):
    """Get templates by category"""
    try:
        if not template_engine.initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        templates = template_engine.get_templates_by_category(category)
        return {
            "category": category,
            "templates": templates,
            "total": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error getting templates for category {category}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get templates for category: {str(e)}")


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    return template_engine.get_status()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002) 