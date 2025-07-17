"""
Jr Dev Agent LangGraph Implementation

This module implements the core LangGraph workflow for the Jr Dev Agent.
It orchestrates the entire process from ticket fetching to prompt generation.
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from langgraph_mcp.utils.load_ticket_metadata import load_ticket_metadata
from langgraph_mcp.nodes.jira_prompt_node import JiraPromptNode
from langgraph_mcp.services.prompt_builder import PromptBuilder
from langgraph_mcp.services.template_engine import TemplateEngine


class JrDevState(TypedDict):
    """
    State definition for Jr Dev Agent LangGraph
    
    This represents the state that flows through the LangGraph workflow.
    """
    # Input data
    ticket_id: str
    session_id: str
    
    # Ticket data
    ticket_data: Dict[str, Any]
    
    # Processing state
    current_step: str
    steps_completed: List[str]
    
    # Generated outputs
    prompt: str
    prompt_hash: str
    template_used: str
    
    # Metadata
    processing_start: datetime
    processing_time_ms: int
    errors: List[str]
    metadata: Dict[str, Any]


class JrDevGraph:
    """
    LangGraph implementation for Jr Dev Agent workflow
    
    This class orchestrates the entire workflow from ticket fetching
    to prompt generation using LangGraph's state management.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.graph = None
        self.prompt_builder = PromptBuilder()
        self.template_engine = TemplateEngine()
        self.jira_prompt_node = JiraPromptNode()
        
    async def initialize(self):
        """Initialize the LangGraph workflow"""
        self.logger.info("Initializing Jr Dev Agent LangGraph...")
        
        # Initialize services
        await self.prompt_builder.initialize()
        await self.template_engine.initialize()
        
        # Build the graph
        self.graph = self._build_graph()
        
        self.logger.info("Jr Dev Agent LangGraph initialized successfully")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow
        
        The workflow follows these steps:
        1. fetch_ticket - Get ticket metadata
        2. select_template - Choose appropriate template
        3. enrich_context - Add synthetic memory context (future)
        4. generate_prompt - Create the final prompt
        5. finalize - Prepare response
        """
        
        # Create the graph
        workflow = StateGraph(JrDevState)
        
        # Add nodes
        workflow.add_node("fetch_ticket", self._fetch_ticket_node)
        workflow.add_node("select_template", self._select_template_node)
        workflow.add_node("enrich_context", self._enrich_context_node)
        workflow.add_node("generate_prompt", self._generate_prompt_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Define the flow
        workflow.set_entry_point("fetch_ticket")
        workflow.add_edge("fetch_ticket", "select_template")
        workflow.add_edge("select_template", "enrich_context")
        workflow.add_edge("enrich_context", "generate_prompt")
        workflow.add_edge("generate_prompt", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def process_ticket(self, ticket_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Process a ticket through the LangGraph workflow
        
        Args:
            ticket_data: Raw ticket data
            session_id: Session identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            self.logger.info(f"Processing ticket {ticket_data['ticket_id']} in session {session_id}")
            
            # Initialize state
            initial_state = JrDevState(
                ticket_id=ticket_data['ticket_id'],
                session_id=session_id,
                ticket_data=ticket_data,
                current_step="initialize",
                steps_completed=[],
                prompt="",
                prompt_hash="",
                template_used="",
                processing_start=datetime.now(),
                processing_time_ms=0,
                errors=[],
                metadata={}
            )
            
            # Run the workflow
            result = await self.graph.ainvoke(initial_state)
            
            # Calculate processing time
            processing_time = (datetime.now() - result['processing_start']).total_seconds() * 1000
            result['processing_time_ms'] = int(processing_time)
            
            self.logger.info(f"Successfully processed ticket {ticket_data['ticket_id']} in {processing_time:.0f}ms")
            
            return {
                "prompt": result['prompt'],
                "hash": result['prompt_hash'],
                "template_used": result['template_used'],
                "processing_time_ms": result['processing_time_ms'],
                "steps_completed": result['steps_completed'],
                "metadata": result['metadata']
            }
            
        except Exception as e:
            self.logger.error(f"Error processing ticket {ticket_data['ticket_id']}: {str(e)}")
            raise
    
    async def _fetch_ticket_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Fetch ticket metadata
        
        This node fetches or validates ticket metadata using our existing
        fallback system.
        """
        try:
            self.logger.info(f"Fetching ticket metadata for {state['ticket_id']}")
            
            # Use our existing fallback system
            if not state['ticket_data']:
                ticket_data = load_ticket_metadata(state['ticket_id'])
                state['ticket_data'] = ticket_data
            
            # Validate required fields
            required_fields = ['ticket_id', 'summary', 'description']
            for field in required_fields:
                if field not in state['ticket_data']:
                    raise ValueError(f"Missing required field: {field}")
            
            state['current_step'] = "fetch_ticket"
            state['steps_completed'].append("fetch_ticket")
            
            self.logger.info(f"Successfully fetched ticket metadata for {state['ticket_id']}")
            
        except Exception as e:
            error_msg = f"Error fetching ticket metadata: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
        
        return state
    
    async def _select_template_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Select appropriate template
        
        This node determines which template to use based on the ticket metadata.
        """
        try:
            self.logger.info(f"Selecting template for {state['ticket_id']}")
            
            # Get template name from ticket data or use default
            template_name = state['ticket_data'].get('template_name', 'feature')
            
            # Validate template exists
            if not self.template_engine.has_template(template_name):
                self.logger.warning(f"Template {template_name} not found, using 'feature' as fallback")
                template_name = 'feature'
            
            state['template_used'] = template_name
            state['current_step'] = "select_template"
            state['steps_completed'].append("select_template")
            
            self.logger.info(f"Selected template '{template_name}' for {state['ticket_id']}")
            
        except Exception as e:
            error_msg = f"Error selecting template: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
        
        return state
    
    async def _enrich_context_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Enrich context with synthetic memory
        
        This node will eventually integrate with the Synthetic Memory system
        to add context and related information to the prompt.
        """
        try:
            self.logger.info(f"Enriching context for {state['ticket_id']}")
            
            # Placeholder for future Synthetic Memory integration
            # enriched_data = await synthetic_memory.enrich_context(state['ticket_data'])
            
            # For now, just add some basic enrichment
            enrichment_data = {
                "context_enriched": True,
                "enrichment_timestamp": datetime.now().isoformat(),
                "complexity_score": 0.5,  # Default complexity
                "related_files": [],  # Will be populated by Synthetic Memory
                "related_tickets": []  # Will be populated by Synthetic Memory
            }
            
            state['metadata']['enrichment'] = enrichment_data
            state['current_step'] = "enrich_context"
            state['steps_completed'].append("enrich_context")
            
            self.logger.info(f"Successfully enriched context for {state['ticket_id']}")
            
        except Exception as e:
            error_msg = f"Error enriching context: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            # Continue processing even if enrichment fails
        
        return state
    
    async def _generate_prompt_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Generate the final prompt
        
        This node uses the PromptBuilder to generate the final AI-optimized prompt
        using the selected template and enriched context.
        """
        try:
            self.logger.info(f"Generating prompt for {state['ticket_id']}")
            
            # Generate prompt using PromptBuilder
            prompt = await self.prompt_builder.generate_prompt(
                template_name=state['template_used'],
                ticket_data=state['ticket_data'],
                enrichment_data=state['metadata'].get('enrichment', {})
            )
            
            # Generate hash for the prompt
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
            
            state['prompt'] = prompt
            state['prompt_hash'] = prompt_hash
            state['current_step'] = "generate_prompt"
            state['steps_completed'].append("generate_prompt")
            
            self.logger.info(f"Successfully generated prompt for {state['ticket_id']} (hash: {prompt_hash})")
            
        except Exception as e:
            error_msg = f"Error generating prompt: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
        
        return state
    
    async def _finalize_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Finalize processing
        
        This node performs final cleanup and preparation of the response.
        """
        try:
            self.logger.info(f"Finalizing processing for {state['ticket_id']}")
            
            # Add final metadata
            state['metadata']['finalized_at'] = datetime.now().isoformat()
            state['metadata']['total_steps'] = len(state['steps_completed'])
            state['metadata']['success'] = len(state['errors']) == 0
            
            state['current_step'] = "finalize"
            state['steps_completed'].append("finalize")
            
            self.logger.info(f"Successfully finalized processing for {state['ticket_id']}")
            
        except Exception as e:
            error_msg = f"Error finalizing processing: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
        
        return state
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the LangGraph system
        
        Returns:
            Dictionary with health information
        """
        try:
            return {
                "status": "healthy",
                "graph_initialized": self.graph is not None,
                "prompt_builder": self.prompt_builder.get_status(),
                "template_engine": self.template_engine.get_status(),
                "jira_prompt_node": self.jira_prompt_node.get_status()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "graph_initialized": False
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up Jr Dev Agent LangGraph...")
        
        # Cleanup services
        await self.prompt_builder.cleanup()
        await self.template_engine.cleanup()
        
        self.logger.info("Jr Dev Agent LangGraph cleanup complete")
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow structure
        
        Returns:
            Dictionary with workflow information
        """
        return {
            "nodes": [
                "fetch_ticket",
                "select_template", 
                "enrich_context",
                "generate_prompt",
                "finalize"
            ],
            "entry_point": "fetch_ticket",
            "edges": [
                "fetch_ticket -> select_template",
                "select_template -> enrich_context",
                "enrich_context -> generate_prompt",
                "generate_prompt -> finalize",
                "finalize -> END"
            ],
            "description": "Jr Dev Agent workflow for converting Jira tickets to AI-optimized prompts"
        } 