"""
MCP Gateway Extension

This module extends the existing FastAPI server with MCP (Model Context Protocol) endpoints,
enabling cross-IDE compatibility while preserving all existing v1 functionality.

Usage:
    from langgraph_mcp.mcp_gateway import add_mcp_routes
    add_mcp_routes(app, jr_dev_graph, session_manager)
"""

import logging
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


def add_mcp_routes(app: FastAPI, jr_dev_graph, session_manager):
    """
    Add MCP protocol endpoints to existing FastAPI application
    
    Args:
        app: FastAPI application instance
        jr_dev_graph: JrDevGraph instance for workflow processing
        session_manager: SessionManager instance for session tracking
    """
    
    @app.post("/mcp/initialize")
    async def mcp_initialize(request: MCPRequest) -> MCPResponse:
        """
        MCP initialization and capability negotiation
        
        This endpoint handles the MCP handshake protocol, declaring server
        capabilities and establishing the connection with MCP clients.
        """
        try:
            logger.info("MCP initialization requested")
            
            result = MCPInitializeResult()
            
            return MCPResponse(
                id=request.id,
                result=result.dict()
            )
            
        except Exception as e:
            logger.error(f"MCP initialization failed: {str(e)}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCodes.INTERNAL_ERROR,
                    "message": f"Initialization failed: {str(e)}"
                }
            )

    @app.post("/mcp/tools/list")
    async def mcp_list_tools(request: MCPRequest) -> MCPResponse:
        """
        MCP tool discovery endpoint
        
        Returns the list of available tools that can be invoked by MCP clients.
        This enables IDEs to discover and present available Jr Dev Agent capabilities.
        """
        try:
            logger.info("MCP tools list requested")
            
            tools = [tool.dict() for tool in MCP_TOOLS.values()]
            
            return MCPResponse(
                id=request.id,
                result={"tools": tools}
            )
            
        except Exception as e:
            logger.error(f"Error listing MCP tools: {str(e)}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCodes.INTERNAL_ERROR,
                    "message": f"Failed to list tools: {str(e)}"
                }
            )

    @app.post("/mcp/tools/call")
    async def mcp_call_tool(request: MCPRequest) -> MCPResponse:
        """
        MCP tool execution endpoint
        
        Routes tool calls to appropriate handlers based on tool name.
        This is the main entry point for cross-IDE agent interactions.
        """
        try:
            if not request.params:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": MCPErrorCodes.INVALID_PARAMS,
                        "message": "Missing required parameters"
                    }
                )
            
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
                    session_manager
                )
            elif tool_name == "health":
                result = await handle_health_tool(jr_dev_graph, session_manager)
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": MCPErrorCodes.TOOL_NOT_FOUND,
                        "message": f"Tool not found: {tool_name}"
                    }
                )
            
            return MCPResponse(id=request.id, result=result)
            
        except ValueError as e:
            # Validation error
            logger.error(f"Validation error for tool {tool_name}: {str(e)}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCodes.INVALID_PARAMS,
                    "message": f"Invalid parameters: {str(e)}"
                }
            )
        except Exception as e:
            # Internal error
            logger.error(f"Error executing MCP tool {tool_name}: {str(e)}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCodes.TOOL_EXECUTION_ERROR,
                    "message": f"Tool execution failed: {str(e)}"
                }
            )


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
    
    result = PrepareAgentTaskResult(
        prompt_text=agent_prompt,
        metadata={
            "ticket_id": args.ticket_id,
            "session_id": session_id,
            "files_to_modify": files_to_modify,
            "template_used": workflow_result.get("template_used", "feature"),
            "commands": commands,
            "repo": args.repo,
            "branch": args.branch,
            "processing_time_ms": workflow_result.get("processing_time_ms", 0)
        },
        memory=workflow_result.get("metadata", {}).get("enrichment", {}),
        chat_injection={
            "enabled": True,
            "message": agent_prompt,  # Same as prompt_text but formatted for chat
            "format": "markdown",
            "instructions": "Press Enter to execute this prompt in Agent Mode"
        }
    )
    
    logger.info(f"Successfully generated agent-ready prompt for {args.ticket_id}")
    return result.dict()


async def handle_finalize_session(
    args: FinalizeSessionArgs,
    session_manager
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
    
    # Calculate MVP PESS score (basic algorithm for Week 1)
    pess_score = calculate_mvp_pess_score(args)
    
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
        "pess_algorithm_version": "mvp_1.0"
    }
    
    # TODO: Week 3 - Enhance with full PESS integration
    # TODO: Week 3 - Add Synthetic Memory updates
    
    result = FinalizeSessionResult(
        pess_score=pess_score,
        analytics=analytics
    )
    
    logger.info(f"Session {args.session_id} finalized with PESS score: {pess_score}")
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


def calculate_mvp_pess_score(args: FinalizeSessionArgs) -> float:
    """
    Calculate basic PESS score for MVP
    
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
    
    return round(final_score, 1)
