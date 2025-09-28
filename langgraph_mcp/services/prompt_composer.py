"""
Prompt Composer for Jr Dev Agent

This module handles the composition of final prompts with Memory Context and Read-before-edit sections
as specified in the Layer 2 - Agent "Self-Serve" instructions.
"""

import logging
from typing import Dict, List, Any


class PromptComposer:
    """
    Composes final prompts with Memory Context and Read-before-edit sections.
    
    This implements Layer 2 of the Synthetic Memory integration, adding specific
    actionable instructions for the Coding Agent.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the prompt composer"""
        self.logger.info("PromptComposer initialized")
    
    def compose_final_prompt(self, base_prompt: str, memory_envelope: Dict[str, Any], files_to_modify: List[str] = None) -> str:
        """
        Compose final prompt with Memory Context and Read-before-edit sections.
        
        This implements the exact pattern specified in the requirements:
        - Original prompt content
        - Memory Context section (from MemoryEnvelope) 
        - Read-before-edit section (local file guidance)
        
        Args:
            base_prompt: Original prompt text from PromptBuilder
            memory_envelope: MemoryEnvelope with enrichment data
            files_to_modify: Optional list of files to modify
            
        Returns:
            Enhanced prompt with memory context and file guidance
        """
        if not memory_envelope:
            return base_prompt
            
        # Build memory context section
        memory_section = self._build_memory_context_section(memory_envelope)
        
        # Build read-before-edit section
        files_list = files_to_modify or self._extract_files_from_memory(memory_envelope)
        read_before_edit_section = self._build_read_before_edit_section(files_list, memory_envelope)
        
        # Compose final prompt
        enhanced_prompt = f"""{base_prompt}

{memory_section}

{read_before_edit_section}"""

        return enhanced_prompt
    
    def _build_memory_context_section(self, memory_envelope: Dict[str, Any]) -> str:
        """
        Build Memory Context section from MemoryEnvelope.
        
        Format matches the specification exactly:
        ## Memory Context (from syntheticMemory/)
        Feature: enable_sla_on_shipping
        • Connected features: pfs_shipping, sla_config_flag
        • Related nodes: ...
        • Prior runs: ...
        • Complexity: 0.83
        """
        feature_id = memory_envelope.get("feature_id", "unknown")
        connected_features = memory_envelope.get("connected_features", [])
        related_nodes = memory_envelope.get("related_nodes", {})
        prior_runs = memory_envelope.get("prior_runs", [])
        complexity_score = memory_envelope.get("complexity_score", 0.5)
        
        section = f"""## Memory Context (from syntheticMemory/)

Feature: {feature_id}"""
        
        # Connected features
        if connected_features:
            features_str = ", ".join(connected_features)
            section += f"\n\t• Connected features: {features_str}"
        else:
            section += f"\n\t• Connected features: None"
            
        # Related nodes
        if related_nodes:
            section += f"\n\t• Related nodes:"
            for node, connections in related_nodes.items():
                if connections:
                    connections_str = ", ".join(connections)
                    section += f"\n\t\t• {node} ↔ {connections_str}"
                else:
                    section += f"\n\t\t• {node} (standalone)"
        else:
            section += f"\n\t• Related nodes: None"
            
        # Prior runs
        if prior_runs:
            section += f"\n\t• Prior runs:"
            for run in prior_runs[:3]:  # Show top 3 runs
                ticket_id = run.get("ticket_id", "unknown")
                result = run.get("result", "unknown") 
                score = run.get("score", 0)
                if isinstance(score, (int, float)):
                    score_str = f"score {score:.2f}" if score > 1 else f"score {score:.2f}"
                else:
                    score_str = "no score"
                section += f"\n\t\t• {ticket_id} ({result}, {score_str})"
                
                # Add file context if available
                files_touched = run.get("files_touched", [])
                if files_touched and len(files_touched) <= 3:
                    files_str = ", ".join(files_touched)
                    section += f" touched {files_str}"
                elif len(files_touched) > 3:
                    section += f" touched {len(files_touched)} files"
        else:
            section += f"\n\t• Prior runs: None"
            
        # Complexity score
        section += f"\n\t• Complexity: {complexity_score}"
        
        return section
    
    def _build_read_before_edit_section(self, files_to_modify: List[str], memory_envelope: Dict[str, Any]) -> str:
        """
        Build Read-before-edit section with explicit agent steps.
        
        Format matches specification:
        ## Read-before-edit (local file guidance)  
        1. Open ce-cartxo/src/global-utils/setup-runtime-config.utils.ts and locate existing CCM boolean patterns...
        2. Open shippingStrategiesResolver.ts and update resolver to include sla resolution path...
        """
        if not files_to_modify:
            return """## Read-before-edit (local file guidance)

No specific files identified. Proceed with scoped modifications based on ticket requirements."""

        section = """## Read-before-edit (local file guidance)"""
        
        # Get file hints from memory envelope
        file_hints = memory_envelope.get("file_hints", [])
        hint_map = {hint["path"]: hint["note"] for hint in file_hints}
        
        # Generate numbered instructions for each file
        for i, file_path in enumerate(files_to_modify, 1):
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            
            # Get specific hint for this file or generate generic one
            if file_path in hint_map:
                guidance = hint_map[file_path]
            else:
                guidance = self._generate_file_guidance(file_path, file_name)
            
            section += f"\n\t{i}. Open {file_path} and {guidance}"
        
        return section
    
    def _generate_file_guidance(self, file_path: str, file_name: str) -> str:
        """
        Generate generic file guidance based on file type/pattern.
        
        Returns appropriate guidance for common file types.
        """
        # CCM/config files
        if "setup-runtime-config" in file_path or "ccm" in file_path.lower():
            return "locate existing CCM boolean patterns; insert the flag without altering other flags."
            
        # GraphQL resolvers
        elif "resolver" in file_path.lower():
            if "mutation" in file_path.lower() or "update" in file_name.lower():
                return "update mutation resolver to accept new input parameters with proper validation and CCM guards."
            else:
                return "update resolver to include new field resolution with CCM feature flag protection."
                
        # Test files  
        elif "test" in file_path.lower():
            return "add test coverage for the new functionality with CCM flag on/off scenarios."
            
        # GraphQL schema files
        elif file_path.endswith(('.graphql', '.gql')):
            return "update schema definitions to include new types/fields as specified."
            
        # TypeScript/JavaScript files
        elif file_path.endswith(('.ts', '.js')):
            return "implement the required functionality following existing patterns and conventions."
            
        # Generic fallback
        else:
            return "review and update according to ticket requirements while maintaining existing patterns."
    
    def _extract_files_from_memory(self, memory_envelope: Dict[str, Any]) -> List[str]:
        """
        Extract file list from memory envelope if not provided separately.
        
        Returns list of files from prior runs or file hints.
        """
        files = set()
        
        # Get files from file hints
        file_hints = memory_envelope.get("file_hints", [])
        for hint in file_hints:
            if "path" in hint:
                files.add(hint["path"])
        
        # Get files from related nodes
        related_nodes = memory_envelope.get("related_nodes", {})
        for node in related_nodes.keys():
            files.add(node)
            
        return list(files)
    
    def format_memory_context_for_no_memory(self) -> str:
        """
        Format memory context section when no memory is found.
        
        Provides guardrail message as specified in requirements.
        """
        return """## Memory Context (from syntheticMemory/)

No prior memory found for this feature; proceed with scoped modifications."""
