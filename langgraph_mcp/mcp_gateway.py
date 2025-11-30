"""
MCP Gateway Extension

This module extends the existing FastAPI server with MCP (Model Context Protocol) endpoints,
enabling cross-IDE compatibility while preserving all existing v1 functionality.

Usage:
    from langgraph_mcp.mcp_gateway import add_mcp_routes
    add_mcp_routes(app, jr_dev_graph, session_manager)
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from langgraph_mcp.models.mcp import (
    MCPRequest, MCPResponse, MCPToolDefinition, MCPErrorCodes,
    PrepareAgentTaskArgs, PrepareAgentTaskResult,
    FinalizeSessionArgs, FinalizeSessionResult,
    HealthToolResult, MCPInitializeResult
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
    
    from fastapi.responses import StreamingResponse
    import json
    
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
                "sse": "GET /sse"
            }
        }
    
    @app.get("/sse")
    async def mcp_sse():
        """
        SSE (Server-Sent Events) endpoint for Cursor MCP integration
        
        Keeps connection open and handles MCP protocol via SSE.
        """
        async def event_generator():
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
            
            # Keep connection alive
            import asyncio
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        
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
    async def mcp_root(request: MCPRequest) -> Dict[str, Any]:
        """
        Root MCP endpoint for HTTP-based MCP clients
        
        Routes JSON-RPC requests to appropriate handlers.
        """
        request_data = request.dict()
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
        
        This endpoint handles the MCP handshake protocol, declaring server
        capabilities and establishing the connection with MCP clients.
        """
        try:
            logger.info("MCP initialization requested")
            
            result = MCPInitializeResult()
            
            return _success(request.id, result.dict())
            
        except Exception as e:
            logger.error(f"MCP initialization failed: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Initialization failed: {str(e)}")

    @app.post("/mcp/tools/list", response_model=None)
    async def mcp_list_tools(request: MCPRequest) -> Dict[str, Any]:
        """
        MCP tool discovery endpoint
        
        Returns the list of available tools that can be invoked by MCP clients.
        This enables IDEs to discover and present available Jr Dev Agent capabilities.
        """
        try:
            logger.info("MCP tools list requested")
            
            tools = [tool.dict() for tool in MCP_TOOLS.values()]
            
            return _success(request.id, {"tools": tools})
            
        except Exception as e:
            logger.error(f"Error listing MCP tools: {str(e)}")
            return _error(request.id, MCPErrorCodes.INTERNAL_ERROR, f"Failed to list tools: {str(e)}")

    @app.post("/mcp/tools/call", response_model=None)
    async def mcp_call_tool(request: MCPRequest) -> Dict[str, Any]:
        """
        MCP tool execution endpoint
        
        Routes tool calls to appropriate handlers based on tool name.
        This is the main entry point for cross-IDE agent interactions.
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
                    branch=arguments.get("branch")
                )
                
                # Call the shared logic
                # Note: handle_prepare_agent_task returns a dict with "content" and "_meta"
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
                
                # Format as GetPromptResult
                result = {
                    "description": MCP_PROMPTS["prepare_agent_task"]["description"],
                    "messages": [
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



async def handle_prepare_agent_task(
    args: PrepareAgentTaskArgs, 
    jr_dev_graph, 
    session_manager
) -> Dict[str, Any]:
    """
    Handle prepare_agent_task tool - generate agent-ready prompt
    
    This is the core MCP tool that transforms Jira tickets into executable prompts.
    It reuses the existing v1 LangGraph workflow while formatting output for agents.
    
    Args:
        args: Tool arguments containing ticket_id and optional repo/branch
        jr_dev_graph: LangGraph workflow instance
        session_manager: Session tracking instance
        
    Returns:
        Dictionary containing prompt_text, metadata, and memory data
    """
    logger.info(f"Processing prepare_agent_task for ticket: {args.ticket_id}")
    
    # Create new session for this MCP request
    session_id = f"mcp_{args.ticket_id}_{uuid.uuid4().hex[:8]}"
    
    session_manager.create_session(
        ticket_id=args.ticket_id,
        metadata={
            "source": "mcp_gateway",
            "repo": args.repo,
            "branch": args.branch,
            "mcp_session": True
        }
    )
    
    # Load full ticket data first
    from langgraph_mcp.utils.load_ticket_metadata import load_ticket_metadata
    
    try:
        # Load complete ticket metadata
        full_ticket_data = load_ticket_metadata(args.ticket_id)
        logger.info(f"Loaded ticket data for {args.ticket_id}: {list(full_ticket_data.keys())}")
        
        # Process ticket through existing LangGraph workflow
        # This reuses all your existing v1 logic!
        workflow_result = await jr_dev_graph.process_ticket(
            ticket_data=full_ticket_data,
            session_id=session_id
        )
        
        # Validate workflow result
        if not workflow_result:
            raise ValueError("LangGraph workflow returned None result")
        
        if "prompt" not in workflow_result:
            raise ValueError(f"LangGraph workflow missing 'prompt' field: {workflow_result}")
        
        # Transform workflow result into agent-ready format
        agent_prompt = format_prompt_for_agent(
            prompt=workflow_result["prompt"],
            metadata=workflow_result.get("metadata", {}),
            template_used=workflow_result.get("template_used", "feature")
        )
        
        # Extract actionable metadata for agent execution
        files_to_modify = extract_files_from_prompt(workflow_result["prompt"])
        commands = extract_commands_from_prompt(workflow_result["prompt"])
        
    except Exception as workflow_error:
        logger.error(f"LangGraph workflow error: {str(workflow_error)}")
        raise ValueError(f"Failed to process ticket through workflow: {str(workflow_error)}")
    
    result = {
        "content": [
            {
                "type": "text",
                "text": agent_prompt
            }
        ],
        "_meta": {
            "prompt_text": agent_prompt,
            "metadata": {
                "ticket_id": args.ticket_id,
                "session_id": session_id,
                "files_to_modify": files_to_modify,
                "template_used": workflow_result.get("template_used", "feature"),
                "commands": commands,
                "repo": args.repo,
                "branch": args.branch,
                "processing_time_ms": workflow_result.get("processing_time_ms", 0)
            },
            "memory": workflow_result.get("metadata", {}).get("enrichment", {}),
            "chat_injection": {
                "enabled": True,
                "message": agent_prompt,
                "format": "markdown",
                "instructions": "Press Enter to execute this prompt in Agent Mode"
            }
        }
    }
    
    logger.info(f"Successfully generated agent-ready prompt for {args.ticket_id}")
    return result


async def handle_finalize_session(
    args: FinalizeSessionArgs,
    session_manager,
    jr_dev_graph=None,
    confluence_client=None,
) -> Dict[str, Any]:
    """
    Handle finalize_session tool - complete session and trigger analytics
    
    This tool marks sessions as complete and triggers PESS scoring and
    memory updates. For MVP, we implement basic scoring that can be enhanced.
    
    Args:
        args: Finalization arguments including session data and metrics
        session_manager: Session tracking instance
        
    Returns:
        Dictionary containing PESS score and analytics data
    """
    logger.info(f"Finalizing session: {args.session_id}")
    
    # Update session with completion information
    try:
        session_manager.complete_session(
            session_id=args.session_id,
            pr_url=args.pr_url,
            completed_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.warning(f"Could not update session {args.session_id}: {str(e)}")
    
    pess_result: Dict[str, Any] = {}
    pess_score_percent: float

    # Prefer full PESS client when available
    if jr_dev_graph and hasattr(jr_dev_graph, "pess_client"):
        try:
            pess_result = await jr_dev_graph.pess_client.score_session_completion(
                ticket_id=args.ticket_id,
                session_id=args.session_id,
                pr_url=args.pr_url,
                files_modified=args.files_modified,
                processing_time_ms=args.duration_ms,
                retry_count=args.retry_count,
                feedback=args.feedback,
                agent_telemetry=args.agent_telemetry,
            )
        except Exception as e:
            logger.warning(f"PESS service unavailable, falling back to MVP scoring: {str(e)}")
            pess_result = {}

    if not pess_result:
        pess_result = calculate_mvp_pess_score(args)

    # Normalise score helpers
    prompt_score = pess_result.get("prompt_score", 0.0)
    if "score_percent" in pess_result:
        pess_score_percent = pess_result["score_percent"]
    else:
        pess_score_percent = round(prompt_score * 100, 1)
        pess_result["score_percent"] = pess_score_percent

    if "prompt_score" not in pess_result:
        pess_result["prompt_score"] = round(pess_score_percent / 100.0, 2)
    
    # Prepare analytics data
    analytics = {
        "session_id": args.session_id,
        "ticket_id": args.ticket_id,
        "completion_timestamp": datetime.now().isoformat(),
        "files_modified_count": len(args.files_modified),
        "retry_count": args.retry_count,
        "manual_edits": args.manual_edits,
        "duration_ms": args.duration_ms,
        "memory_updated": True,  # Always true for MVP
        "pess_algorithm_version": pess_result.get("algorithm_version", "mvp_1.0"),
        "feedback": args.feedback,
        "agent_telemetry": args.agent_telemetry,
        "pess_score_percent": pess_score_percent,
        "pess_result": pess_result,
    }

    # Update synthetic memory with final completion data
    if jr_dev_graph and hasattr(jr_dev_graph, "synthetic_memory"):
        try:
            await jr_dev_graph.synthetic_memory.record_completion(
                ticket_id=args.ticket_id,
                pr_url=args.pr_url or "",
                pess_score=pess_result.get("prompt_score", 0.5),
                metadata={
                    "session_id": args.session_id,
                    "files_modified": args.files_modified,
                    "retry_count": args.retry_count,
                    "manual_edits": args.manual_edits,
                    "duration_ms": args.duration_ms,
                    "feedback": args.feedback,
                    "agent_telemetry": args.agent_telemetry,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to persist synthetic memory completion: {str(e)}")

    # Trigger Confluence update (mocked locally when not configured)
    confluence_update = None
    if confluence_client is None:
        from langgraph_mcp.clients import ConfluenceMCPClient

        confluence_client = ConfluenceMCPClient()

    try:
        update_body = compose_confluence_update(args.ticket_id, args, pess_result)
        if update_body:
            page_id = os.getenv("CONFLUENCE_TEMPLATE_PAGE_ID", args.ticket_id)
            confluence_update = confluence_client.update_template(
                page_id=page_id,
                new_body=update_body,
                metadata={
                    "ticket_id": args.ticket_id,
                    "session_id": args.session_id,
                    "pess_score_percent": pess_score_percent,
                },
            )
            analytics["confluence_update"] = confluence_update
    except Exception as e:
        logger.warning(f"Confluence update failed: {str(e)}")

    result = FinalizeSessionResult(
        pess_score=round(pess_score_percent, 1),
        analytics=analytics,
        confluence_update=confluence_update,
    )
    
    logger.info(
        f"Session {args.session_id} finalized",
        extra={"pess_score_percent": pess_score_percent, "ticket_id": args.ticket_id},
    )
    return result.dict()


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
        mcp_tools_available=len(MCP_TOOLS)
    )
    
    return result.dict()


# Helper functions for prompt processing
def format_prompt_for_agent(prompt: str, metadata: Dict[str, Any], template_used: str) -> str:
    """
    Format the generated prompt for agent consumption
    
    Ensures the prompt is immediately executable by Copilot Agent Mode
    without requiring human editing or interpretation.
    """
    # Add agent-specific instructions
    agent_header = f"""# 🤖 Agent Execution Mode - {template_used.upper()}

**IMPORTANT**: This prompt is designed for immediate agent execution. 
Please execute all steps systematically and create a PR when complete.

---

"""
    
    # Add success criteria section
    success_footer = """

---

## ✅ Completion Criteria

1. **All acceptance criteria met** - Verify each requirement is implemented
2. **Tests passing** - Run test suite and ensure no regressions  
3. **Code quality maintained** - Follow existing patterns and conventions
4. **Pull request created** - Include descriptive title and summary

**When finished, create a pull request with:**
- Clear title referencing the ticket ID
- Summary of changes made
- Link to this ticket in the description

You may use the "Mark Complete" button in the IDE to finalize the session.
"""
    
    return agent_header + prompt + success_footer


def extract_files_from_prompt(prompt: str) -> List[str]:
    """Extract file paths mentioned in the prompt"""
    files = []
    
    # Look for common file patterns in prompt
    import re
    
    # Pattern 1: Files listed with bullets (- path/to/file.ext)
    bullet_files = re.findall(r'^-\s+([^\s]+\.[a-zA-Z]+)$', prompt, re.MULTILINE)
    files.extend(bullet_files)
    
    # Pattern 2: Files mentioned in markdown code blocks
    code_files = re.findall(r'`([^`]+\.[a-zA-Z]+)`', prompt)
    files.extend(code_files)
    
    # Pattern 3: Common file extensions in paths
    path_files = re.findall(r'([a-zA-Z0-9/_.-]+\.[a-zA-Z]+)', prompt)
    files.extend([f for f in path_files if '/' in f])  # Only paths, not just extensions
    
    # Remove duplicates and filter common paths
    unique_files = list(set(files))
    filtered_files = [f for f in unique_files if not f.startswith('http') and len(f) > 3]
    
    return filtered_files[:10]  # Limit to 10 most relevant files


def extract_commands_from_prompt(prompt: str) -> List[str]:
    """Extract CLI commands mentioned in the prompt"""
    commands = []
    
    # Common commands patterns
    command_patterns = [
        r'npm run (\w+)',
        r'npm (\w+)',
        r'yarn (\w+)',
        r'pnpm (\w+)',
        r'python -m (\w+)',
        r'pytest',
        r'jest',
        r'tsc',
        r'eslint',
        r'prettier'
    ]
    
    for pattern in command_patterns:
        import re
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        if pattern == r'npm run (\w+)':
            commands.extend([f"npm run {match}" for match in matches])
        elif pattern == r'npm (\w+)':
            commands.extend([f"npm {match}" for match in matches])
        elif pattern == r'yarn (\w+)':
            commands.extend([f"yarn {match}" for match in matches])
        elif pattern == r'pnpm (\w+)':
            commands.extend([f"pnpm {match}" for match in matches])
        else:
            commands.extend(matches)
    
    # Add common commands if not already present
    if 'test' in prompt.lower() and not any('test' in cmd for cmd in commands):
        commands.append('npm test')
    
    if 'generate' in prompt.lower() and not any('generate' in cmd for cmd in commands):
        commands.append('npm run generate')
    
    return list(set(commands))  # Remove duplicates


def compose_confluence_update(
    ticket_id: str,
    args: FinalizeSessionArgs,
    pess_result: Dict[str, Any],
) -> str:
    """
    Compose the updated Confluence template body summarising the session.

    For local development this returns Markdown; in production the content can
    be transformed to whatever storage format the MCP requires.
    """
    score_percent = pess_result.get("score_percent", 0)
    clarity = pess_result.get("clarity_rating", "unknown")
    recommendation = pess_result.get("recommendation")
    feedback = args.feedback or pess_result.get("feedback")

    lines = [
        f"# Jr Dev Agent Session Summary – {ticket_id}",
        "",
        f"- **Session ID**: {args.session_id}",
        f"- **PESS Score**: {score_percent}",
        f"- **Clarity Rating**: {clarity}",
        f"- **Files Modified**: {len(args.files_modified)}",
        f"- **Retries**: {args.retry_count}",
        f"- **Manual edits**: {args.manual_edits}",
        f"- **Duration (ms)**: {args.duration_ms}",
    ]

    if recommendation:
        lines.extend(["", f"**Recommendations:** {recommendation}"])

    if feedback:
        lines.extend(["", "## Developer Feedback", feedback])

    if args.agent_telemetry:
        lines.extend(["", "## Agent Telemetry"])
        for key, value in args.agent_telemetry.items():
            lines.append(f"- **{key}**: {value}")

    lines.extend(["", "_Updated automatically by Jr Dev Agent MCP._"])
    return "\n".join(lines)


def calculate_mvp_pess_score(args: FinalizeSessionArgs) -> Dict[str, Any]:
    """
    Calculate basic PESS score for MVP and return a structured result.
    
    This is a simplified scoring algorithm that will be enhanced in Week 3
    with the full PESS system integration.
    """
    base_score = 85.0  # Start with good score
    
    # Retry penalty (5 points per retry)
    if args.retry_count > 0:
        base_score -= min(args.retry_count * 5, 20)  # Cap at -20 points
    
    # Manual edit penalty (2 points per edit)
    if args.manual_edits > 0:
        base_score -= min(args.manual_edits * 2, 15)  # Cap at -15 points
    
    # Duration bonus/penalty
    if args.duration_ms > 0:
        minutes = args.duration_ms / (1000 * 60)
        if minutes < 5:  # Very fast completion
            base_score += 5
        elif minutes > 30:  # Slow completion
            base_score -= 10
    
    # File modification bonus (shows agent was productive)
    if len(args.files_modified) > 0:
        base_score += min(len(args.files_modified) * 2, 10)  # Up to +10 points
    
    # PR creation bonus
    if args.pr_url:
        base_score += 5
    
    # Ensure score is within valid range
    final_score = max(0.0, min(100.0, base_score))
    clarity = (
        "High"
        if final_score >= 85
        else "Medium"
        if final_score >= 70
        else "Low"
        if final_score >= 50
        else "Very Low"
    )

    recommendation = "Continue iterating on this template."
    if final_score >= 90:
        recommendation = "Template performing exceptionally well – capture as best practice."
    elif final_score <= 60:
        recommendation = "Consider refining requirements and acceptance criteria for clarity."
    
    return {
        "prompt_score": round(final_score / 100.0, 2),
        "score_percent": round(final_score, 1),
        "clarity_rating": clarity,
        "recommendation": recommendation,
        "feedback": args.feedback,
        "retry_count": args.retry_count,
        "files_modified": len(args.files_modified),
        "mock_response": True,
        "algorithm_version": "mvp_1.0",
    }
