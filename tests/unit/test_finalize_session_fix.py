
import pytest
from unittest.mock import AsyncMock, MagicMock
from jr_dev_agent.tools.finalize_session import handle_finalize_session
from jr_dev_agent.models.mcp import FinalizeSessionArgs

@pytest.mark.asyncio
async def test_finalize_session_uses_feedback_from_args():
    """
    Verify that handle_finalize_session uses the feedback from the arguments
    and does not try to read it from the result object (which triggered AttributeError).
    """
    # Mock dependencies
    mock_session_manager = MagicMock()
    mock_jr_dev_graph = MagicMock()
    
    # Mock PESS client on the graph
    mock_pess_client = AsyncMock()
    mock_pess_client.score_session_completion.return_value = {
        "prompt_score": 0.95,
        "score_percent": 95.0,
        "clarity_rating": "High",
        "recommendation": "Good job"
    }
    mock_jr_dev_graph.pess_client = mock_pess_client
    
    # Mock Synthetic Memory
    mock_synthetic_memory = AsyncMock()
    mock_synthetic_memory.record_completion.return_value = True
    mock_jr_dev_graph.synthetic_memory = mock_synthetic_memory

    # Input arguments with feedback
    args = FinalizeSessionArgs(
        session_id="test-session",
        ticket_id="TEST-123",
        files_modified=["test.py"],
        duration_ms=1000,
        feedback="This is my feedback",
        retry_count=0,
        manual_edits=0
    )

    # Execute the handler
    result = await handle_finalize_session(
        args=args,
        session_manager=mock_session_manager,
        jr_dev_graph=mock_jr_dev_graph
    )

    # Verify the result structure
    assert "content" in result
    assert len(result["content"]) > 0
    text_content = result["content"][0]["text"]
    
    # CRITICAL CHECK: The feedback from args should be in the text output
    assert "Feedback: This is my feedback" in text_content
    
    # Verify PESS score is present
    assert "_meta" in result
    assert result["_meta"]["pess_score"] == 95.0
