"""
Jr Dev Agent LangGraph Implementation

This module implements the core LangGraph workflow for the Jr Dev Agent.
It orchestrates the entire process from ticket fetching to prompt generation.
"""

import hashlib
import logging
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from langgraph_mcp.utils.load_ticket_metadata import load_ticket_metadata
from langgraph_mcp.nodes.jira_prompt_node import JiraPromptNode
from langgraph_mcp.services.prompt_builder import PromptBuilder
from langgraph_mcp.services.template_engine import TemplateEngine
from langgraph_mcp.services.synthetic_memory import SyntheticMemory
from langgraph_mcp.services.pess_client import PESSClient
from langgraph_mcp.services.prompt_composer import PromptComposer


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
        self.synthetic_memory = SyntheticMemory()
        self.pess_client = PESSClient()
        self.prompt_composer = PromptComposer()
        
    async def initialize(self):
        """Initialize the LangGraph workflow"""
        self.logger.info("Initializing Jr Dev Agent LangGraph...")
        
        # Initialize services
        await self.prompt_builder.initialize()
        await self.template_engine.initialize()
        await self.synthetic_memory.initialize()
        await self.pess_client.initialize()
        await self.prompt_composer.initialize()
        
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
            
            # Record session start for PESS tracking
            await self.pess_client.record_session_start(
                ticket_data['ticket_id'], 
                session_id, 
                {"source": "langgraph_workflow"}
            )
            
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
                processing_start=datetime.now(timezone.utc),
                processing_time_ms=0,
                errors=[],
                metadata={}
            )
            
            # Run the workflow
            result = await self.graph.ainvoke(initial_state)
            
            # Calculate processing time (timezone-aware, tolerate naive start)
            start_dt = result['processing_start']
            if getattr(start_dt, 'tzinfo', None) is None or start_dt.tzinfo.utcoffset(start_dt) is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            processing_time = (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
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
        
        This node integrates with the Synthetic Memory system to add context
        and related information to the prompt based on previous development sessions.
        """
        try:
            self.logger.info(f"Enriching context for {state['ticket_id']}")
            
            # Use Synthetic Memory v2 to enrich context
            enrichment_data = await self.synthetic_memory.enrich_context(state['ticket_data'])
            
            state['metadata']['enrichment'] = enrichment_data or {}
            state['current_step'] = "enrich_context" 
            state['steps_completed'].append("enrich_context")
            
            # Log enrichment details (spec-aligned)
            memory_envelope = (enrichment_data or {}).get('memory_envelope', {})
            if (enrichment_data or {}).get('context_enriched') and memory_envelope:
                complexity = memory_envelope.get('complexity_score', 0)
                related_nodes = len(memory_envelope.get('related_nodes', []))
                features_count = len(memory_envelope.get('connected_features', []))
                self.logger.info(
                    f"Enriched: feature={memory_envelope.get('feature_id','unknown')}, "
                    f"complexity={complexity:.2f}, related_nodes={related_nodes}, "
                    f"connected_features={features_count}"
                )
            else:
                self.logger.warning(f"No prior memory context available for {state['ticket_id']}")
            
        except Exception as e:
            error_msg = f"Error enriching context: {str(e)}"
            state['errors'].append(error_msg)
            self.logger.error(error_msg)
            
            # Provide fallback enrichment data (spec-aligned)
            state['metadata']['enrichment'] = {
                "context_enriched": False,
                "error": str(e),
                "enrichment_timestamp": time.time(),
                "memory_envelope": {
                    "feature_id": "unknown",
                    "complexity_score": 0.5,
                    "related_nodes": [],
                    "connected_features": [],
                    "prior_runs": [],
                    "file_hints": []
                }
            }
        
        return state
    
    def _extract_files_to_modify(self, ticket_data: Dict[str, Any]) -> List[str]:
        """
        Extract files to modify from ticket data.
        
        Returns list of files that the agent should focus on.
        """
        files = []
        
        # 1) Highest precedence: agent_guardrails.file_allowlist
        allowlist = (ticket_data.get('agent_guardrails') or {}).get('file_allowlist') or []
        if isinstance(allowlist, list):
            files.extend(allowlist)

        # 2) files_affected
        fa = ticket_data.get('files_affected')
        if isinstance(fa, list):
            files.extend(fa)
        elif isinstance(fa, str):
            files.append(fa)
        
        # Check metadata for file references  
        if 'metadata' in ticket_data and 'file_references' in ticket_data['metadata']:
            files.extend(ticket_data['metadata']['file_references'])
        
        # 4) Parse files from description if available
        description = ticket_data.get('description', '')
        if description:
            # Look for file patterns like src/path/to/file.ts or similar
            file_patterns = re.findall(r'[\w\-/]+\.[a-zA-Z0-9]{1,6}', description)
            files.extend(file_patterns)
        
        # Deduplicate and filter out invalid files
        unique_files = []
        seen = set()
        for file in files:
            if file and file not in seen and '.' in file:  # Must have an extension
                unique_files.append(file)
                seen.add(file)
        
        return unique_files
    
    async def _generate_prompt_node(self, state: JrDevState) -> JrDevState:
        """
        Node: Generate the final prompt with Memory Context and Read-before-edit sections
        
        This node implements the enhanced prompt generation with:
        1. Base prompt from PromptBuilder 
        2. Memory Context from MemoryEnvelope
        3. Read-before-edit guidance for Agent Mode
        """
        try:
            self.logger.info(f"Generating prompt for {state['ticket_id']}")
            
            # Generate base prompt using PromptBuilder
            base_prompt = await self.prompt_builder.generate_prompt(
                template_name=state['template_used'],
                ticket_data=state['ticket_data'],
                enrichment_data=state['metadata'].get('enrichment', {})
            )
            
            # Extract MemoryEnvelope from enrichment data
            enrichment_data = state['metadata'].get('enrichment', {})
            memory_envelope = enrichment_data.get('memory_envelope', {})
            
            # Extract files to modify from ticket data
            files_to_modify = self._extract_files_to_modify(state['ticket_data'])
            state['metadata']['files_to_modify'] = files_to_modify

            # Capture commands (if any)
            commands = state['ticket_data'].get('commands', [])
            if isinstance(commands, list):
                state['metadata']['commands'] = commands
            elif isinstance(commands, str):
                state['metadata']['commands'] = [commands]
            else:
                state['metadata']['commands'] = []
            
            # Compose final prompt with Memory Context and Read-before-edit sections
            if memory_envelope and memory_envelope.get('feature_id') != 'unknown':
                enhanced_prompt = self.prompt_composer.compose_final_prompt(
                    base_prompt=base_prompt,
                    memory_envelope=memory_envelope,
                    files_to_modify=files_to_modify
                )
                self.logger.info(f"Enhanced prompt with memory context for feature: {memory_envelope.get('feature_id')}")
            else:
                # Add minimal memory context when no memory available
                no_memory_context = self.prompt_composer.format_memory_context_for_no_memory()
                enhanced_prompt = f"{base_prompt}\n\n{no_memory_context}"
                self.logger.info(f"Generated prompt with no prior memory context")
            
            # Generate hash from the enhanced prompt (full + short)
            full_hash = hashlib.sha256(enhanced_prompt.encode()).hexdigest()
            prompt_hash = full_hash[:16]
            
            state['prompt'] = enhanced_prompt
            state['prompt_hash'] = prompt_hash
            state['metadata']['prompt_hash_full'] = full_hash
            state['current_step'] = "generate_prompt"
            state['steps_completed'].append("generate_prompt")
            
            # Record prompt generation for PESS tracking
            try:
                await self.pess_client.record_prompt_generated(
                    ticket_id=state['ticket_id'],
                    session_id=state['session_id'],
                    prompt_hash=prompt_hash,
                    template_used=state['template_used'],
                    enrichment_data=enrichment_data
                )
            except Exception as e:
                self.logger.warning(f"Failed to record prompt generation in PESS: {str(e)}")
            
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
        
        This node performs final cleanup, PESS scoring, and preparation of the response.
        """
        try:
            self.logger.info(f"Finalizing processing for {state['ticket_id']}")
            
            # Calculate processing time (timezone-aware, tolerate naive start)
            start_dt = state['processing_start']
            if getattr(start_dt, 'tzinfo', None) is None or start_dt.tzinfo.utcoffset(start_dt) is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            processing_time_ms = int((datetime.now(timezone.utc) - start_dt).total_seconds() * 1000)
            
            # Record PESS completion scoring
            try:
                pess_result = await self.pess_client.score_session_completion(
                    ticket_id=state['ticket_id'],
                    session_id=state['session_id'],
                    processing_time_ms=processing_time_ms,
                    retry_count=1  # Default for LangGraph workflow
                )
                state['metadata']['pess_score'] = pess_result
                self.logger.info(f"PESS scoring completed for {state['ticket_id']}: {pess_result.get('prompt_score', 'N/A')}")
            except Exception as e:
                self.logger.warning(f"PESS scoring failed for {state['ticket_id']}: {str(e)}")
                state['metadata']['pess_score'] = {"error": str(e), "mock_response": True}
            
            # Record completion in synthetic memory
            try:
                await self.synthetic_memory.record_completion(
                    ticket_id=state['ticket_id'],
                    pr_url="",  # Will be provided later via finalize_session
                    pess_score=state['metadata']['pess_score'].get('prompt_score', 0.5),
                    metadata={
                        "session_id": state['session_id'],
                        "template_used": state['template_used'],
                        "processing_time_ms": processing_time_ms
                    }
                )
            except Exception as e:
                self.logger.warning(f"Failed to record completion in synthetic memory: {str(e)}")
            
            # Add final metadata
            state['metadata']['finalized_at'] = datetime.now(timezone.utc).isoformat()
            state['metadata']['total_steps'] = len(state['steps_completed'])
            state['metadata']['success'] = len(state['errors']) == 0
            state['metadata']['processing_time_ms'] = processing_time_ms
            
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
                "jira_prompt_node": self.jira_prompt_node.get_status(),
                "synthetic_memory": getattr(self.synthetic_memory, 'get_status', lambda: {"initialized": True})(),
                "pess_client": getattr(self.pess_client, 'get_status', lambda: {"initialized": True})(),
                "prompt_composer": getattr(self.prompt_composer, 'get_status', lambda: {"initialized": True})()
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