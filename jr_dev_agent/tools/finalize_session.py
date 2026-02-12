import logging
import os
from datetime import datetime
from typing import Dict, Any

from jr_dev_agent.models.mcp import FinalizeSessionArgs, FinalizeSessionResult

logger = logging.getLogger(__name__)

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

    # Retrieve session to get project_root if available
    session = session_manager.get_session(args.session_id)
    project_root = session.metadata.get("project_root") if session and session.metadata else None

    # Update synthetic memory with final completion data
    if jr_dev_graph:
        # Determine memory service to use
        memory_service = jr_dev_graph.synthetic_memory
        
        # If project_root is specified for this session, use a temporary instance pointing to it
        if project_root:
            from jr_dev_agent.services.synthetic_memory import SyntheticMemory
            memory_root = os.path.join(project_root, "syntheticMemory")
            memory_service = SyntheticMemory(root=memory_root, backend="fs")
            await memory_service.initialize()
            logger.info(f"Using session-specific memory root: {memory_root}")

        try:
            await memory_service.record_completion(
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
                change_required=args.change_required,
                changes_made=args.changes_made
            )
        except Exception as e:
            logger.warning(f"Failed to persist synthetic memory completion: {str(e)}")

    # Trigger Confluence update (mocked locally when not configured)
    confluence_update = None
    
    # NEW: Determine if template update is needed based on PESS score
    template_update_request = None
    
    # Threshold for template update recommendation (e.g. < 80%)
    TEMPLATE_UPDATE_THRESHOLD = 80.0
    
    if pess_score_percent < TEMPLATE_UPDATE_THRESHOLD:
        # Get template name from metadata or guess based on what we have
        template_name = "feature" # Default fallback
        if session and session.metadata and "template_used" in session.metadata:
            template_name = session.metadata["template_used"]
            
        template_update_request = {
            "required": True,
            "template_name": template_name,
            "reason": f"PESS score ({pess_score_percent}%) is below threshold ({TEMPLATE_UPDATE_THRESHOLD}%). "
                      f"Feedback: {args.feedback or 'None'}. "
                      f"Retries: {args.retry_count}. "
                      "Please analyze the failure patterns and propose an updated template."
        }
        logger.info(f"Triggering template update request for {template_name} (Score: {pess_score_percent}%)")

    # Legacy Confluence update logic (kept for backward compatibility if client configured)
    if confluence_client is None:
        try:
            from jr_dev_agent.clients import ConfluenceMCPClient
            confluence_client = ConfluenceMCPClient()
        except ImportError:
            pass # Client might not exist in pure MCP setup

    if confluence_client:
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
        template_update_request=template_update_request
    )
    
    # Format message to Agent
    response_text = f"Session finalized for {args.ticket_id}.\nPESS Score: {pess_score_percent}%\n"
    
    if args.feedback:
        response_text += f"Feedback: {args.feedback}\n"
    
    if template_update_request:
        response_text += (
            "\n⚠️ **TEMPLATE UPDATE REQUIRED** ⚠️\n"
            f"The PESS score is below the quality threshold ({pess_score_percent}% < 80%).\n"
            "You must now IMPROVE the prompt template to prevent this in the future.\n\n"
            "**Instructions:**\n"
            "1. Analyze the `full_prompt` in `agent_run.json` and the user feedback.\n"
            "2. Identify why the previous prompt failed or needed retries.\n"
            f"3. Generate an improved version of the `{template_update_request['template_name']}` template.\n"
            "4. Use the `create_template_pr` tool to submit your improvements.\n"
        )
    
    # Format as valid MCP CallToolResult
    return {
        "content": [
            {
                "type": "text",
                "text": response_text
            }
        ],
        "_meta": result.model_dump()
    }


def compose_confluence_update(
    ticket_id: str,
    args: FinalizeSessionArgs,
    pess_result: Dict[str, Any],
) -> str:
    """
    Compose the updated Confluence template body summarising the session.
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

