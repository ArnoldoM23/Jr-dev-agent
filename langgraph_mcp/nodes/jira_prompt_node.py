"""
🚀 Jr Dev Agent - LangGraph Jira Prompt Node
=============================================

This module contains the LangGraph node that handles Jira ticket fetching
with integrated fallback mechanism. It's designed to work seamlessly with
the MVP Jira Fallback Flow.

Author: Jr Dev Agent Team
Version: 1.0
"""

from typing import Dict, Any, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import structlog
from dataclasses import dataclass
from datetime import datetime
import os

# Import our fallback system
from ..utils.load_ticket_metadata import (
    load_ticket_metadata,
    validate_ticket_metadata,
    get_fallback_status,
    JiraFallbackError
)

# Setup structured logging
logger = structlog.get_logger(__name__)

@dataclass
class JiraPromptState:
    """State for the Jira prompt node"""
    ticket_id: str
    ticket_metadata: Dict[str, Any] = None
    template_name: str = ""
    prompt_text: str = ""
    error: str = ""
    fallback_used: bool = False
    retry_count: int = 0
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LangGraph state"""
        return {
            "ticket_id": self.ticket_id,
            "ticket_metadata": self.ticket_metadata,
            "template_name": self.template_name,
            "prompt_text": self.prompt_text,
            "error": self.error,
            "fallback_used": self.fallback_used,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp
        }

class JiraPromptNode:
    """
    LangGraph node for handling Jira ticket fetching with fallback.
    
    This node integrates with the MVP Jira Fallback Flow to ensure
    developers can continue working even when MCP or Jira is unavailable.
    """
    
    def __init__(self):
        """Initialize the Jira prompt node"""
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.max_retries = int(os.getenv("JIRA_MAX_RETRIES", "3"))
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Jira prompt node.
        
        Args:
            state: LangGraph state dictionary
            
        Returns:
            Updated state dictionary
        """
        ticket_id = state.get("ticket_id")
        if not ticket_id:
            return self._handle_error(state, "No ticket ID provided")
        
        retry_count = state.get("retry_count", 0)
        
        self.logger.info(
            "Executing Jira prompt node",
            ticket_id=ticket_id,
            retry_count=retry_count,
            max_retries=self.max_retries
        )
        
        try:
            # Load ticket metadata with fallback
            metadata = load_ticket_metadata(ticket_id)
            
            # Validate metadata
            validated_metadata = validate_ticket_metadata(metadata)
            
            # Check if fallback was used
            fallback_used = metadata.get("_fallback_used", False)
            
            # Update state with successful result
            updated_state = {
                **state,
                "ticket_metadata": metadata,
                "template_name": validated_metadata.template_name,
                "error": "",
                "fallback_used": fallback_used,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
            self.logger.info(
                "Successfully loaded ticket metadata",
                ticket_id=ticket_id,
                template_name=validated_metadata.template_name,
                fallback_used=fallback_used,
                retry_count=retry_count
            )
            
            return updated_state
            
        except JiraFallbackError as e:
            return self._handle_fallback_error(state, str(e), retry_count)
            
        except ValueError as e:
            return self._handle_validation_error(state, str(e))
            
        except Exception as e:
            return self._handle_unexpected_error(state, str(e), retry_count)
    
    def _handle_error(self, state: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Handle general errors"""
        self.logger.error(
            "Jira prompt node error",
            ticket_id=state.get("ticket_id"),
            error=error_msg
        )
        
        return {
            **state,
            "error": error_msg,
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_fallback_error(self, state: Dict[str, Any], error_msg: str, retry_count: int) -> Dict[str, Any]:
        """Handle fallback-specific errors"""
        if retry_count < self.max_retries:
            self.logger.warning(
                "Fallback error - retrying",
                ticket_id=state.get("ticket_id"),
                error=error_msg,
                retry_count=retry_count,
                max_retries=self.max_retries
            )
            
            return {
                **state,
                "retry_count": retry_count + 1,
                "error": f"Retry {retry_count + 1}: {error_msg}",
                "status": "retrying"
            }
        else:
            self.logger.error(
                "Fallback error - max retries exceeded",
                ticket_id=state.get("ticket_id"),
                error=error_msg,
                retry_count=retry_count
            )
            
            return self._handle_error(state, f"Max retries exceeded: {error_msg}")
    
    def _handle_validation_error(self, state: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Handle validation errors"""
        self.logger.error(
            "Ticket validation error",
            ticket_id=state.get("ticket_id"),
            error=error_msg
        )
        
        return self._handle_error(state, f"Validation error: {error_msg}")
    
    def _handle_unexpected_error(self, state: Dict[str, Any], error_msg: str, retry_count: int) -> Dict[str, Any]:
        """Handle unexpected errors"""
        if retry_count < self.max_retries:
            self.logger.warning(
                "Unexpected error - retrying",
                ticket_id=state.get("ticket_id"),
                error=error_msg,
                retry_count=retry_count
            )
            
            return {
                **state,
                "retry_count": retry_count + 1,
                "error": f"Retry {retry_count + 1}: {error_msg}",
                "status": "retrying"
            }
        else:
            return self._handle_error(state, f"Unexpected error: {error_msg}")

def jira_prompt_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for Jira ticket processing.
    
    This is the main entry point for the LangGraph DAG.
    
    Args:
        state: Current LangGraph state
        
    Returns:
        Updated state with ticket metadata
    """
    node = JiraPromptNode()
    return node(state)

def create_jira_prompt_graph() -> StateGraph:
    """
    Create a LangGraph state graph for Jira prompt processing.
    
    Returns:
        Configured StateGraph for Jira processing
    """
    # Define the graph
    graph = StateGraph(Dict[str, Any])
    
    # Add nodes
    graph.add_node("jira_fetch", jira_prompt_node)
    graph.add_node("status_check", status_check_node)
    
    # Add edges
    graph.add_edge(START, "jira_fetch")
    graph.add_conditional_edges(
        "jira_fetch",
        should_retry,
        {
            "retry": "jira_fetch",
            "success": "status_check",
            "error": END
        }
    )
    graph.add_edge("status_check", END)
    
    return graph.compile()

def should_retry(state: Dict[str, Any]) -> str:
    """
    Determine if the node should retry based on state.
    
    Args:
        state: Current state
        
    Returns:
        Next node name or "END"
    """
    status = state.get("status", "")
    retry_count = state.get("retry_count", 0)
    max_retries = int(os.getenv("JIRA_MAX_RETRIES", "3"))
    
    if status == "retrying" and retry_count < max_retries:
        return "retry"
    elif status == "success":
        return "success"
    else:
        return "error"

def status_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final status check node.
    
    Args:
        state: Current state
        
    Returns:
        Final state with status information
    """
    ticket_id = state.get("ticket_id")
    fallback_used = state.get("fallback_used", False)
    
    logger.info(
        "Jira prompt processing completed",
        ticket_id=ticket_id,
        fallback_used=fallback_used,
        template_name=state.get("template_name"),
        final_status=state.get("status")
    )
    
    # Add final metadata
    final_state = {
        **state,
        "completed_at": datetime.now().isoformat(),
        "final_status": state.get("status", "unknown")
    }
    
    return final_state

def get_jira_node_status() -> Dict[str, Any]:
    """
    Get status information about the Jira node and fallback system.
    
    Returns:
        Dictionary with status information
    """
    fallback_status = get_fallback_status()
    
    return {
        "node_version": "1.0",
        "max_retries": int(os.getenv("JIRA_MAX_RETRIES", "3")),
        "fallback_system": fallback_status,
        "dev_mode": os.getenv("DEV_MODE", "false").lower() == "true",
        "jira_mcp_url": os.getenv("JIRA_MCP_URL", "https://mcp.walmart.com/api/jira"),
        "timestamp": datetime.now().isoformat()
    }

# Example usage and testing
if __name__ == "__main__":
    # Test the Jira prompt node
    print("🧪 Testing Jr Dev Agent - LangGraph Jira Prompt Node")
    print("=" * 55)
    
    # Test state
    test_state = {
        "ticket_id": "CEPG-67890",
        "retry_count": 0
    }
    
    try:
        # Test node status
        status = get_jira_node_status()
        print(f"📊 Node Status: {status}")
        
        # Test node execution
        node = JiraPromptNode()
        result = node(test_state)
        
        print(f"✅ Node execution completed")
        print(f"📋 Template: {result.get('template_name')}")
        print(f"🔄 Fallback used: {result.get('fallback_used', False)}")
        print(f"📊 Status: {result.get('status')}")
        
        if result.get("error"):
            print(f"❌ Error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


class JiraPromptNode:
    """
    Jira Prompt Node for LangGraph integration
    
    This class provides a simple wrapper around the Jira prompt functionality
    for integration with the LangGraph MCP server.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.initialized = True
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the Jira prompt node"""
        try:
            fallback_status = get_fallback_status()
            
            return {
                "initialized": self.initialized,
                "service": "JiraPromptNode",
                "version": "1.0.0",
                "fallback_available": fallback_status.get("fallback_available", False),
                "fallback_file_path": fallback_status.get("fallback_file_path", ""),
                "dev_mode": os.getenv("DEV_MODE", "false").lower() == "true"
            }
        except Exception as e:
            return {
                "initialized": False,
                "service": "JiraPromptNode",
                "version": "1.0.0",
                "error": str(e)
            }
    
    async def process_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Process a ticket through the Jira prompt node
        
        Args:
            ticket_id: The ticket ID to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Load ticket metadata using our existing fallback system
            ticket_metadata = load_ticket_metadata(ticket_id)
            
            # Validate the metadata
            validation_result = validate_ticket_metadata(ticket_metadata)
            
            if not validation_result.get("valid", False):
                raise JiraFallbackError(f"Invalid ticket metadata: {validation_result.get('error', 'Unknown error')}")
            
            return {
                "ticket_id": ticket_id,
                "ticket_metadata": ticket_metadata,
                "template_name": ticket_metadata.get("template_name", "feature"),
                "fallback_used": ticket_metadata.get("fallback_used", False),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
            return {
                "ticket_id": ticket_id,
                "error": str(e),
                "status": "error"
            } 