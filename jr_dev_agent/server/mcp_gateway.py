"""
MCP Gateway Extension

This module extends the existing FastAPI server with MCP (Model Context Protocol) endpoints,
enabling cross-IDE compatibility while preserving all existing v1 functionality.

Usage:
    from jr_dev_agent.server.mcp_gateway import add_mcp_routes
    add_mcp_routes(app, jr_dev_graph, session_manager)
"""

import logging
import json
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from jr_dev_agent.models.mcp import (
    MCPRequest, MCPResponse, MCPToolDefinition, MCPErrorCodes,
    PrepareAgentTaskArgs, FinalizeSessionArgs, MCPInitializeResult
)
from jr_dev_agent.tools import (
    handle_prepare_agent_task,
    handle_finalize_session,
    handle_health_tool
)

logger = logging.getLogger(__name__)

# MCP Tool Registry - Available tools for cross-IDE agents
MCP_TOOLS = {
    "prepare_agent_task": MCPToolDefinition(
        name="prepare_agent_task",
        description="Generate agent-ready prompt from Jira ticket for immediate execution",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "pattern": "^[A-Z]+-\\d+$",
                    "description": "Jira ticket ID (e.g., CEPG-12345)"
                },
                "repo": {
                    "type": "string", 
                    "description": "Repository name (optional)"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (optional)"
                },
                "project_root": {
                    "type": "string",
                    "description": "Path to the project root directory (for memory storage)"
                },
                "fallback_template_content": {
                    "type": "string",
                    "description": "Content of local fallback template file (e.g. jira_ticket_template.txt) if present on client. The agent should read the file and pass its content here."
                }
            },
            "required": ["ticket_id"]
        }
    ),
    
    "finalize_session": MCPToolDefinition(
        name="finalize_session",
        description="Complete development session and trigger PESS scoring + memory updates",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
                "ticket_id": {"type": "string", "description": "Ticket identifier"},
                "pr_url": {"type": "string", "description": "Pull request URL (optional)"},
                "files_modified": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of files that were modified"
                },
                "retry_count": {
                    "type": "integer", 
                    "minimum": 0,
                    "description": "Number of retry attempts"
                },
                "manual_edits": {
                    "type": "integer",
                    "minimum": 0, 
                    "description": "Number of manual edits made"
                },
                "duration_ms": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Total session duration in milliseconds"
                },
                "feedback": {
                    "type": "string",
                    "description": "Developer feedback or qualitative notes about the run"
                },
                "agent_telemetry": {
                    "type": "object",
                    "description": "Raw telemetry emitted by the coding agent (retries, commands, etc.)"
                }
            },
            "required": ["session_id", "ticket_id"]
        }
    ),
    
    "health": MCPToolDefinition(
        name="health",
        description="Check gateway and backend service health status",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    )
}

# MCP Prompt Registry - Templates for chat injection
MCP_PROMPTS = {
    "prepare_agent_task": {
        "name": "prepare_agent_task",
        "description": "Generate agent-ready prompt from Jira ticket",
        "arguments": [
            {
                "name": "ticket_id",
                "description": "Jira ticket ID (e.g. CEPG-67890)",
                "required": True
            }
        ]
    }
}


def add_mcp_routes(app: FastAPI, jr_dev_graph, session_manager):
    """
    Add MCP protocol endpoints to existing FastAPI application
    
    Args:
        app: FastAPI application instance
        jr_dev_graph: JrDevGraph instance for workflow processing
        session_manager: SessionManager instance for session tracking
    """
    
    @app.get("/")
    async def mcp_root_get():
        """
        Root GET endpoint - Cursor tries this first to discover the server
        
        Returns server info and available endpoints.
        """
        return {
            "name": "jrdev-gateway",
            "version": "2.0.0",
            "description": "Jr Dev Agent MCP Gateway",
            "protocol": "mcp",
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": True
            },
            "endpoints": {
                "initialize": "POST /",
                "tools_list": "POST /",
                "tools_call": "POST /",
                "mcp": "GET /mcp"
            }
        }
    
    @app.get("/mcp")
    async def mcp_endpoint():
        """
        MCP endpoint for Cursor MCP integration
        
        Keeps connection open and handles MCP protocol via server-sent events.
        """
        async def event_generator():
            # Send initial connection message
            # Use endpoint='/' to tell client to POST all JSON-RPC messages to root
            yield f"event: endpoint\ndata: http://127.0.0.1:8000/\n\n"
            
            # Keep connection alive
            import asyncio
            try:
                while True:
                    await asyncio.sleep(30)
                    yield f"event: ping\ndata: {json.dumps({'type': 'ping'})}\n\n"
            except asyncio.CancelledError:
                logger.info("MCP connection closed by client")
                raise
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    @app.post("/", response_model=None)
    @app.post("/mcp", response_model=None)  # Handle POST to /mcp as well to support fallback/defaults
    async def mcp_root(request: MCPRequest) -> Dict[str, Any]:
        """
        Root MCP endpoint for HTTP-based MCP clients
        
        Routes JSON-RPC requests to appropriate handlers.
        """
        request_data = request.model_dump()
        method = request_data.get("method")
        logger.info(f"MCP root received method={method} request={request_data}")
        
        if method == "initialize":
            return await mcp_initialize(request)
        elif method == "tools/list":
            return await mcp_list_tools(request)
        elif method == "tools/call":
            return await mcp_call_tool(request)
        elif method == "prompts/list":
            return await mcp_list_prompts(request)
        elif method == "prompts/get":
            return await mcp_get_prompt(request)
        else:
            return _error(request.id, MCPErrorCodes.METHOD_NOT_FOUND, f"Method not found: {method}")
    
    def _success(id_value, result):
        response = MCPResponse(
            jsonrpc="2.0",
            id=id_value,
            result=result
        )
        return response.model_dump(exclude_none=True)

    def _error(id_value, code, message):
        response = MCPResponse(
            jsonrpc="2.0",
            id=id_value,
            error={
                "code": code,
                "message": message
            }
        )
        return response.model_dump(exclude_none=True)

    @app.post("/mcp/initialize", response_model=None)
    async def mcp_initialize(request: MCPRequest) -> Dict[str, Any]:
        """
        MCP initialization and capability negotiation
        """
        try:
            logger.info("MCP initialization requested")
            
            result = MCPInitializeResult()
            
            return _success(request.id, result.model_dump())
            
        except Exception as e:
            logger.error(f"MCP initialization failed: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Initialization failed: {str(e)}")

    @app.post("/mcp/tools/list", response_model=None)
    async def mcp_list_tools(request: MCPRequest) -> Dict[str, Any]:
        """
        MCP tool discovery endpoint
        """
        try:
            logger.info("MCP tools list requested")
            
            tools = [tool.model_dump() for tool in MCP_TOOLS.values()]
            
            return _success(request.id, {"tools": tools})
            
        except Exception as e:
            logger.error(f"Error listing MCP tools: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Failed to list tools: {str(e)}")

    @app.post("/mcp/tools/call", response_model=None)
    async def mcp_call_tool(request: MCPRequest) -> Dict[str, Any]:
        """
        MCP tool execution endpoint
        """
        try:
            if not request.params:
                return _error(request.id, MCPErrorCodes.INVALID_PARAMS, "Missing required parameters")
            
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            logger.info(f"MCP tool call: {tool_name} with args: {arguments}")
            
            # Route to appropriate tool handler
            if tool_name == "prepare_agent_task":
                result = await handle_prepare_agent_task(
                    PrepareAgentTaskArgs(**arguments),
                    jr_dev_graph,
                    session_manager
                )
            elif tool_name == "finalize_session":
                result = await handle_finalize_session(
                    FinalizeSessionArgs(**arguments),
                    session_manager,
                    jr_dev_graph=jr_dev_graph
                )
            elif tool_name == "health":
                result = await handle_health_tool(jr_dev_graph, session_manager)
            else:
                return _error(request.id, MCPErrorCodes.TOOL_NOT_FOUND, f"Tool not found: {tool_name}")
            
            return _success(request.id, result)
            
        except ValueError as e:
            # Validation error
            logger.error(f"Validation error for tool {tool_name}: {str(e)}")
            return _error(request.id, MCPErrorCodes.INVALID_PARAMS, f"Invalid parameters: {str(e)}")
        except Exception as e:
            # Internal error
            logger.error(f"Error executing MCP tool {tool_name}: {str(e)}")
            return _error(request.id, MCPErrorCodes.TOOL_EXECUTION_ERROR, f"Tool execution failed: {str(e)}")

    @app.post("/mcp/prompts/list", response_model=None)
    async def mcp_list_prompts(request: MCPRequest) -> Dict[str, Any]:
        """List available prompts"""
        try:
            logger.info("MCP prompts list requested")
            prompts = list(MCP_PROMPTS.values())
            return _success(request.id, {"prompts": prompts})
        except Exception as e:
            logger.error(f"Error listing prompts: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Failed to list prompts: {str(e)}")

    @app.post("/mcp/prompts/get", response_model=None)
    async def mcp_get_prompt(request: MCPRequest) -> Dict[str, Any]:
        """Get a specific prompt"""
        try:
            if not request.params:
                return _error(request.id, MCPErrorCodes.INVALID_PARAMS, "Missing required parameters")
            
            prompt_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            logger.info(f"MCP prompt get: {prompt_name} with args: {arguments}")
            
            if prompt_name == "prepare_agent_task":
                # Reuse the tool logic!
                tool_args = PrepareAgentTaskArgs(
                    ticket_id=arguments.get("ticket_id"),
                    repo=arguments.get("repo"),
                    branch=arguments.get("branch"),
                    project_root=arguments.get("project_root"),
                    fallback_template_content=arguments.get("fallback_template_content")
                )
                
                # Call the shared logic
                tool_result = await handle_prepare_agent_task(
                    tool_args,
                    jr_dev_graph,
                    session_manager
                )
                
                # Extract the text content
                content_items = tool_result.get("content", [])
                if not content_items:
                    raise ValueError("No content generated")
                
                prompt_text = content_items[0]["text"]
                
                result = {
                    "description": MCP_PROMPTS["prepare_agent_task"]["description"],
                    "messages": [
                        {
                            "role": "assistant",
                            "content": {
                                "type": "text",
                                "text": "I have generated the agent prompt for this ticket. Please execute it below:"
                            }
                        },
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt_text
                            }
                        }
                    ]
                }
                return _success(request.id, result)
            else:
                return _error(request.id, MCPErrorCodes.INVALID_PARAMS, f"Prompt not found: {prompt_name}")
                
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_name}: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Failed to get prompt: {str(e)}")