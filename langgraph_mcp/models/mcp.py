"""
MCP (Model Context Protocol) Data Models

Pydantic models for handling MCP JSON-RPC 2.0 requests, responses, and tool definitions.
These models ensure compliance with the MCP specification for cross-IDE compatibility.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum


class MCPRequest(BaseModel):
    """
    Base MCP JSON-RPC 2.0 request model
    
    Following JSON-RPC 2.0 specification for MCP protocol compliance.
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to call")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")
    id: Union[str, int, None] = Field(None, description="Request identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "prepare_agent_task",
                    "arguments": {"ticket_id": "CEPG-12345"}
                },
                "id": "request-123"
            }
        }


class MCPResponse(BaseModel):
    """
    Base MCP JSON-RPC 2.0 response model
    
    Handles both successful results and error responses.
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Union[str, int, None] = Field(None, description="Request identifier")
    result: Optional[Dict[str, Any]] = Field(None, description="Success result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error object")

    class Config:
        json_schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "request-123",
                "result": {
                    "prompt_text": "Generated prompt...",
                    "metadata": {"ticket_id": "CEPG-12345"}
                }
            }
        }


class MCPError(BaseModel):
    """MCP error object following JSON-RPC 2.0 error specification"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


class MCPToolDefinition(BaseModel):
    """
    MCP tool definition schema
    
    Defines how tools are registered and discoverable by MCP clients.
    """
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="JSON Schema for tool input")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "prepare_agent_task",
                "description": "Generate agent-ready prompt from Jira ticket",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "pattern": "^[A-Z]+-\\d+$",
                            "description": "Jira ticket ID (e.g., CEPG-12345)"
                        }
                    },
                    "required": ["ticket_id"]
                }
            }
        }


# Tool-specific argument models
class PrepareAgentTaskArgs(BaseModel):
    """
    Arguments for the prepare_agent_task MCP tool
    
    This tool generates agent-ready prompts from Jira tickets.
    """
    ticket_id: str = Field(..., pattern=r"^[A-Z]+-\d+$", description="Jira ticket ID")
    repo: Optional[str] = Field(None, description="Repository name (optional)")
    branch: Optional[str] = Field(None, description="Branch name (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "CEPG-12345",
                "repo": "my-awesome-app",
                "branch": "feature/cepg-12345"
            }
        }


class PrepareAgentTaskResult(BaseModel):
    """
    Result from the prepare_agent_task MCP tool
    
    Contains agent-ready prompt, metadata, and chat injection capabilities.
    """
    prompt_text: str = Field(..., description="Generated agent-ready prompt")
    metadata: Dict[str, Any] = Field(..., description="Execution metadata")
    memory: Optional[Dict[str, Any]] = Field(None, description="Memory enrichment data")
    chat_injection: Dict[str, Any] = Field(..., description="Chat injection configuration for IDEs")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_text": "# 🎯 Development Task: Add pickup option to Order schema\n\n## 📋 Ticket Information\n- **Ticket ID**: CEPG-67890\n- **Priority**: high\n- **Feature**: order_self_pickup\n\n## 📝 Description\nAllow user to select store pickup for their order...\n\n## 📁 Files to Modify\n- src/graphql/types/Order.graphql\n- src/graphql/inputs/OrderInput.graphql\n- src/graphql/resolvers/orderResolver.ts\n\n## 🤖 Instructions for GitHub Copilot\n1. Update OrderInput.graphql to include pickup_store_id field\n2. Update Order.graphql schema to include pickup_store and pickup_time fields\n3. Add validation for pickup_store_id when pickup option is selected\n4. Update GraphQL resolvers to handle pickup logic\n5. Create or update tests as needed\n\n**Commands to run:**\n- npm run generate\n- npm test\n\n**Success criteria:**\n- All acceptance criteria met\n- Tests passing\n- PR created and ready for review",
                "metadata": {
                    "ticket_id": "CEPG-67890",
                    "files_to_modify": [
                        "src/graphql/types/Order.graphql",
                        "src/graphql/inputs/OrderInput.graphql",
                        "src/graphql/resolvers/orderResolver.ts"
                    ],
                    "template_used": "feature_schema_change",
                    "commands": ["npm run generate", "npm test"],
                    "session_id": "mcp_CEPG-67890_abc123"
                },
                "memory": {
                    "complexity_score": 0.74,
                    "related_files": ["Order.graphql", "OrderInput.graphql"],
                    "context_enriched": True
                },
                "chat_injection": {
                    "enabled": True,
                    "message": "# 🎯 Development Task: Add pickup option to Order schema\n\n## 📋 Ticket Information\n- **Ticket ID**: CEPG-67890\n- **Priority**: high\n- **Feature**: order_self_pickup\n\n[... full prompt text ready for agent execution ...]",
                    "format": "markdown"
                }
            }
        }


class FinalizeSessionArgs(BaseModel):
    """
    Arguments for the finalize_session MCP tool
    
    This tool completes the session and triggers analytics/scoring.
    """
    session_id: str = Field(..., description="Session identifier")
    ticket_id: str = Field(..., description="Ticket identifier")
    pr_url: Optional[str] = Field(None, description="Pull request URL")
    files_modified: List[str] = Field(default_factory=list, description="List of modified files")
    retry_count: int = Field(default=0, ge=0, description="Number of retries")
    manual_edits: int = Field(default=0, ge=0, description="Number of manual edits")
    duration_ms: int = Field(default=0, ge=0, description="Session duration in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "mcp_CEPG-67890_abc123",
                "ticket_id": "CEPG-67890",
                "pr_url": "https://github.com/org/repo/pull/123",
                "files_modified": [
                    "src/graphql/types/Order.graphql",
                    "src/graphql/inputs/OrderInput.graphql",
                    "src/graphql/resolvers/orderResolver.ts"
                ],
                "retry_count": 1,
                "manual_edits": 0,
                "duration_ms": 245000
            }
        }


class FinalizeSessionResult(BaseModel):
    """
    Result from the finalize_session MCP tool
    
    Contains PESS score and analytics data.
    """
    pess_score: float = Field(..., description="PESS effectiveness score (0-100)")
    analytics: Dict[str, Any] = Field(..., description="Session analytics data")

    class Config:
        json_schema_extra = {
            "example": {
                "pess_score": 87.5,
                "analytics": {
                    "session_id": "mcp_CEPG-67890_abc123",
                    "ticket_id": "CEPG-67890",
                    "files_modified_count": 3,
                    "retry_count": 1,
                    "manual_edits": 0,
                    "duration_ms": 245000,
                    "memory_updated": True,
                    "template_performance": "good",
                    "completion_timestamp": "2025-08-11T15:30:00Z"
                }
            }
        }


class HealthToolResult(BaseModel):
    """
    Result from the health MCP tool
    
    Contains system health status and service availability.
    """
    status: str = Field(..., description="Overall health status")
    services: Dict[str, str] = Field(..., description="Service status map")
    timestamp: str = Field(..., description="Health check timestamp")
    mcp_tools_available: int = Field(..., description="Number of available MCP tools")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "services": {
                    "langgraph": "available",
                    "session_manager": "available", 
                    "fallback_system": "available",
                    "promptbuilder": "available"
                },
                "timestamp": "2025-08-11T15:30:00Z",
                "mcp_tools_available": 3
            }
        }


# MCP Protocol Constants
class MCPErrorCodes:
    """Standard JSON-RPC 2.0 error codes for MCP"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes
    TOOL_NOT_FOUND = -32000
    TOOL_EXECUTION_ERROR = -32001
    AUTHENTICATION_ERROR = -32002
    RATE_LIMIT_ERROR = -32003


class MCPCapabilities(BaseModel):
    """MCP server capabilities declaration"""
    tools: Dict[str, Any] = Field(default={"listChanged": True})
    resources: Dict[str, Any] = Field(default_factory=dict)
    prompts: Dict[str, Any] = Field(default_factory=dict)


class MCPServerInfo(BaseModel):
    """MCP server information"""
    name: str = Field(default="jrdev-gateway")
    version: str = Field(default="2.0.0")
    description: Optional[str] = Field(default="Jr Dev Agent Cross-IDE Gateway")


class MCPInitializeResult(BaseModel):
    """Result from MCP initialization handshake"""
    protocolVersion: str = Field(default="1.0.0")
    capabilities: MCPCapabilities = Field(default_factory=MCPCapabilities)
    serverInfo: MCPServerInfo = Field(default_factory=MCPServerInfo)

    class Config:
        json_schema_extra = {
            "example": {
                "protocolVersion": "1.0.0",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "jrdev-gateway",
                    "version": "2.0.0",
                    "description": "Jr Dev Agent Cross-IDE Gateway"
                }
            }
        }
