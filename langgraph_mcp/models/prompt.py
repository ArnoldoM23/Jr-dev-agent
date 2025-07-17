"""
Prompt Data Models

Pydantic models for handling prompt generation requests and responses.
These models ensure consistent data structure for the prompt generation API.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from langgraph_mcp.models.ticket import TicketMetadata


class PromptRequest(BaseModel):
    """
    Request model for prompt generation
    
    This model represents a request to generate an AI-optimized prompt
    based on ticket metadata.
    """
    ticket_data: TicketMetadata = Field(..., description="Ticket metadata for prompt generation")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional generation options")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "ticket_data": {
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
                },
                "session_id": "jr_dev_CEPG-12345_abc123",
                "options": {
                    "include_context": True,
                    "complexity_adjustment": "auto",
                    "template_version": "1.0"
                }
            }
        }


class PromptResponse(BaseModel):
    """
    Response model for prompt generation
    
    This model represents the result of prompt generation,
    including the generated prompt and metadata.
    """
    prompt: str = Field(..., description="Generated AI-optimized prompt")
    hash: str = Field(..., description="SHA-256 hash of the generated prompt")
    template_used: str = Field(..., description="Template used for generation")
    generated_at: str = Field(..., description="ISO timestamp of generation")
    metadata: TicketMetadata = Field(..., description="Original ticket metadata")
    processing_info: Dict[str, Any] = Field(default_factory=dict, description="Processing information")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "prompt": "# 🎯 Development Task: Add user authentication feature\n\n## 📋 Ticket Information\n- **Ticket ID**: CEPG-12345\n- **Priority**: High\n- **Feature**: authentication\n- **Assignee**: developer@company.com\n\n## 📝 Description\nImplement OAuth2 authentication for the web application\n\n## ✅ Acceptance Criteria\n- Users can log in with Google OAuth\n- Session management is secure\n- Logout functionality works\n\n## 📁 Files to Modify\n- src/auth/oauth.py\n- src/models/user.py\n- tests/test_auth.py\n\n## 🏷️ Labels & Components\n- **Labels**: feature, security, frontend\n- **Components**: API, Frontend, Database\n\n## 🤖 Instructions for GitHub Copilot\n1. Review the ticket requirements above\n2. Implement the necessary changes in the specified files\n3. Follow best practices for code quality and testing\n4. Ensure all acceptance criteria are met\n5. Create or update tests as needed\n\n## 🔧 Technical Guidelines\n- Use TypeScript for type safety\n- Follow existing code patterns and conventions\n- Add proper error handling\n- Include comprehensive comments\n- Write unit tests for new functionality\n\n**Note**: This prompt was generated using the 'feature' template.",
                "hash": "abc123def456789",
                "template_used": "feature",
                "generated_at": "2024-01-15T10:30:00Z",
                "metadata": {
                    "ticket_id": "CEPG-12345",
                    "template_name": "feature",
                    "summary": "Add user authentication feature",
                    "description": "Implement OAuth2 authentication for the web application",
                    "source": "mcp"
                },
                "processing_info": {
                    "processing_time_ms": 1250,
                    "enrichment_applied": True,
                    "fallback_used": False,
                    "nodes_executed": ["ticket_fetch", "prompt_build", "enrich"],
                    "template_version": "1.0"
                }
            }
        }


class PromptTemplate(BaseModel):
    """
    Model for prompt templates
    
    This model represents a template that can be used to generate
    prompts for different types of tickets.
    """
    name: str = Field(..., description="Template name")
    version: str = Field(..., description="Template version")
    description: str = Field(..., description="Template description")
    template_content: str = Field(..., description="Template content with placeholders")
    required_fields: list = Field(..., description="Required fields for this template")
    optional_fields: list = Field(default_factory=list, description="Optional fields")
    created_at: datetime = Field(default_factory=datetime.now, description="Template creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Template last update time")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "name": "feature",
                "version": "1.0",
                "description": "Template for new feature implementation",
                "template_content": "# 🎯 Development Task: {summary}\n\n## 📋 Ticket Information\n- **Ticket ID**: {ticket_id}\n- **Priority**: {priority}\n- **Feature**: {feature}\n- **Assignee**: {assignee}\n\n## 📝 Description\n{description}\n\n## ✅ Acceptance Criteria\n{acceptance_criteria}\n\n## 📁 Files to Modify\n{files_affected}\n\n## 🏷️ Labels & Components\n- **Labels**: {labels}\n- **Components**: {components}\n\n## 🤖 Instructions for GitHub Copilot\n1. Review the ticket requirements above\n2. Implement the necessary changes in the specified files\n3. Follow best practices for code quality and testing\n4. Ensure all acceptance criteria are met\n5. Create or update tests as needed\n\n## 🔧 Technical Guidelines\n- Use TypeScript for type safety\n- Follow existing code patterns and conventions\n- Add proper error handling\n- Include comprehensive comments\n- Write unit tests for new functionality\n\n**Note**: This prompt was generated using the '{template_name}' template.",
                "required_fields": ["ticket_id", "summary", "description", "priority", "feature", "assignee"],
                "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class PromptGenerationMetrics(BaseModel):
    """
    Model for tracking prompt generation metrics
    
    This model captures performance and quality metrics
    for the prompt generation process.
    """
    session_id: str = Field(..., description="Session identifier")
    ticket_id: str = Field(..., description="Ticket identifier")
    template_used: str = Field(..., description="Template used")
    generation_time_ms: int = Field(..., description="Generation time in milliseconds")
    prompt_length: int = Field(..., description="Generated prompt length in characters")
    enrichment_applied: bool = Field(default=False, description="Whether enrichment was applied")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")
    nodes_executed: list = Field(default_factory=list, description="LangGraph nodes executed")
    error_occurred: bool = Field(default=False, description="Whether an error occurred")
    error_message: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "session_id": "jr_dev_CEPG-12345_abc123",
                "ticket_id": "CEPG-12345",
                "template_used": "feature",
                "generation_time_ms": 1250,
                "prompt_length": 1847,
                "enrichment_applied": True,
                "fallback_used": False,
                "nodes_executed": ["ticket_fetch", "template_select", "prompt_build", "enrich"],
                "error_occurred": False,
                "error_message": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        } 