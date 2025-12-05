import logging
import uuid
import re
from typing import Dict, Any, List

from jr_dev_agent.models.mcp import PrepareAgentTaskArgs

logger = logging.getLogger(__name__)

async def handle_prepare_agent_task(
    args: PrepareAgentTaskArgs, 
    jr_dev_graph, 
    session_manager
) -> Dict[str, Any]:
    """
    Handle prepare_agent_task tool - generate agent-ready prompt
    
    This is the core MCP tool that transforms Jira tickets into executable prompts.
    It reuses the existing v1 LangGraph workflow while formatting output for agents.
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
    from jr_dev_agent.utils.load_ticket_metadata import load_ticket_metadata
    
    try:
        # Load complete ticket metadata
        full_ticket_data = load_ticket_metadata(
            args.ticket_id,
            fallback_content=args.fallback_template_content
        )
        logger.info(f"Loaded ticket data for {args.ticket_id}: {list(full_ticket_data.keys())}")
        
        # Process ticket through existing LangGraph workflow
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


def format_prompt_for_agent(prompt: str, metadata: Dict[str, Any], template_used: str) -> str:
    """
    Format the generated prompt for agent consumption
    """
    agent_header = f"""# 🤖 Agent Execution Mode - {template_used.upper()}

**IMPORTANT**: This prompt is designed for immediate agent execution. 
Please execute all steps systematically and create a PR when complete.

---

"""
    
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

