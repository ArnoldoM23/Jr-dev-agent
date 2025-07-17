"""
Ticket Data Models

Pydantic models for handling ticket metadata throughout the Jr Dev Agent system.
These models ensure consistent data structure and validation.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class TicketMetadata(BaseModel):
    """
    Core ticket metadata model
    
    This model represents the essential information about a Jira ticket
    that's needed for prompt generation and processing.
    """
    ticket_id: str = Field(..., description="Unique ticket identifier (e.g., CEPG-12345)")
    template_name: str = Field(default="feature", description="Template type to use for prompt generation")
    summary: str = Field(..., description="Brief ticket summary")
    description: str = Field(..., description="Detailed ticket description")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria")
    files_affected: List[str] = Field(default_factory=list, description="List of files that may be affected")
    feature: str = Field(default="unknown", description="Feature or component name")
    priority: str = Field(default="Medium", description="Ticket priority level")
    assignee: str = Field(default="unassigned", description="Assigned developer")
    labels: List[str] = Field(default_factory=list, description="Ticket labels")
    components: List[str] = Field(default_factory=list, description="System components affected")
    source: Literal["mcp", "fallback"] = Field(default="mcp", description="Data source (MCP server or fallback)")
    
    @validator('ticket_id')
    def validate_ticket_id(cls, v):
        """Validate ticket ID format"""
        if not v or not isinstance(v, str):
            raise ValueError('ticket_id must be a non-empty string')
        
        # Check for basic format: LETTERS-NUMBERS
        import re
        if not re.match(r'^[A-Z]+-\d+$', v):
            raise ValueError('ticket_id must follow format: PROJECT-123 (e.g., CEPG-12345)')
        
        return v
    
    @validator('template_name')
    def validate_template_name(cls, v):
        """Validate template name"""
        valid_templates = [
            "feature", "bugfix", "refactor", "version_upgrade", 
            "config_update", "schema_change", "resolver_addition",
            "deployment_pipeline", "test_generation"
        ]
        if v not in valid_templates:
            # Allow unknown templates but log a warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown template name: {v}. Using 'feature' as fallback.")
            return "feature"
        return v
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "ticket_id": "CEPG-12345",
                "template_name": "feature",
                "summary": "Add user authentication feature",
                "description": "Implement OAuth2 authentication for the web application",
                "acceptance_criteria": [
                    "Users can log in with Google OAuth",
                    "Session management is secure",
                    "Logout functionality works"
                ],
                "files_affected": [
                    "src/auth/oauth.py",
                    "src/models/user.py",
                    "tests/test_auth.py"
                ],
                "feature": "authentication",
                "priority": "High",
                "assignee": "developer@company.com",
                "labels": ["feature", "security", "frontend"],
                "components": ["API", "Frontend", "Database"],
                "source": "mcp"
            }
        }


class TicketEnrichmentData(BaseModel):
    """
    Extended ticket data with enrichment information
    
    This model includes additional context that may be added
    by the Synthetic Memory system or other enrichment services.
    """
    base_ticket: TicketMetadata = Field(..., description="Base ticket metadata")
    related_tickets: List[str] = Field(default_factory=list, description="Related ticket IDs")
    similar_files: List[str] = Field(default_factory=list, description="Similar files from previous work")
    complexity_score: float = Field(default=0.5, description="Complexity score (0.0-1.0)")
    estimated_effort: str = Field(default="Medium", description="Estimated effort level")
    related_features: List[str] = Field(default_factory=list, description="Related features")
    historical_context: Optional[str] = Field(None, description="Historical context from similar tickets")
    
    @validator('complexity_score')
    def validate_complexity_score(cls, v):
        """Validate complexity score is between 0.0 and 1.0"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('complexity_score must be between 0.0 and 1.0')
        return v
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "base_ticket": {
                    "ticket_id": "CEPG-12345",
                    "template_name": "feature",
                    "summary": "Add user authentication feature",
                    "description": "Implement OAuth2 authentication",
                    "source": "mcp"
                },
                "related_tickets": ["CEPG-12344", "CEPG-12346"],
                "similar_files": ["src/auth/existing_auth.py"],
                "complexity_score": 0.7,
                "estimated_effort": "High",
                "related_features": ["user-management", "security"],
                "historical_context": "Previous OAuth implementation in CEPG-12344"
            }
        }


class TicketProcessingResult(BaseModel):
    """
    Result of ticket processing through the LangGraph workflow
    
    This model represents the output after a ticket has been processed
    through the entire Jr Dev Agent pipeline.
    """
    ticket_id: str = Field(..., description="Processed ticket ID")
    session_id: str = Field(..., description="Processing session ID")
    prompt_generated: str = Field(..., description="Generated AI prompt")
    prompt_hash: str = Field(..., description="Hash of the generated prompt")
    template_used: str = Field(..., description="Template used for generation")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    enrichment_applied: bool = Field(default=False, description="Whether enrichment was applied")
    fallback_used: bool = Field(default=False, description="Whether fallback data was used")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional processing metadata")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "ticket_id": "CEPG-12345",
                "session_id": "jr_dev_CEPG-12345_abc123",
                "prompt_generated": "# Development Task: Add user authentication...",
                "prompt_hash": "abc123def456",
                "template_used": "feature",
                "processing_time_ms": 1250,
                "enrichment_applied": True,
                "fallback_used": False,
                "generated_at": "2024-01-15T10:30:00Z",
                "metadata": {
                    "langgraph_version": "0.1.0",
                    "nodes_executed": ["ticket_fetch", "prompt_build", "enrich"]
                }
            }
        } 