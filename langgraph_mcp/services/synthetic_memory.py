"""
Synthetic Memory Service for Jr Dev Agent

This service provides filesystem-based memory storage with vector DB upgrade path.
Integrates into the LangGraph workflow for context enrichment.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any
from pathlib import Path


class SyntheticMemory:
    """
    Synthetic Memory Service with filesystem backend (MVP) + vector DB ready
    
    This service enriches prompts with contextual information from previous
    development sessions, creating a learning knowledge base.
    """
    
    def __init__(self, root="syntheticMemory", backend="fs"):
        """
        Initialize synthetic memory service.
        
        Args:
            root: Root directory for memory storage
            backend: "fs" for filesystem, "vector" for vector DB
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.backend = backend
        self.initialized = False
        
    async def initialize(self):
        """Initialize the synthetic memory service"""
        self.logger.info("Initializing Synthetic Memory...")
        
        # Load config if available
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                memory_config = config.get("memory", {})
                self.backend = memory_config.get("backend", "fs")
                if self.backend == "fs":
                    self.root = memory_config.get("fs", {}).get("root_dir", "syntheticMemory")
        except FileNotFoundError:
            pass  # Use defaults
            
        # Ensure root directory exists
        os.makedirs(self.root, exist_ok=True)
        
        self.initialized = True
        self.logger.info(f"Synthetic Memory initialized (backend: {self.backend}, root: {self.root})")
    
    async def enrich_context(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ticket context with synthetic memory.
        
        This is the main method called by the LangGraph _enrich_context_node.
        
        Args:
            ticket_data: Raw ticket data from Jira
            
        Returns:
            Enhanced context with memory enrichment data
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            ticket_id = ticket_data.get("ticket_id", "unknown")
            
            # Extract files from ticket data
            files_referenced = self._extract_files_from_ticket(ticket_data)
            
            # Determine feature ID from ticket data
            feature_id = self._determine_feature_id(ticket_data, files_referenced)
            
            # Perform memory enrichment
            memory_data = await self._enrich_memory(ticket_id, feature_id, files_referenced)
            
            # Return enriched context in LangGraph format
            return {
                "context_enriched": True,
                "enrichment_timestamp": time.time(),
                "synthetic_memory": memory_data,
                "complexity_score": memory_data.get("complexity_score", 0.5),
                "related_files": memory_data.get("related_nodes", {}),
                "connected_features": memory_data.get("connected_features", [])
            }
            
        except Exception as e:
            self.logger.error(f"Error enriching context for {ticket_data.get('ticket_id')}: {str(e)}")
            # Return minimal enrichment on error
            return {
                "context_enriched": False,
                "error": str(e),
                "enrichment_timestamp": time.time(),
                "complexity_score": 0.5,
                "related_files": {},
                "connected_features": []
            }
    
    async def _enrich_memory(self, ticket_id: str, feature_id: str, files_referenced: List[str]) -> Dict:
        """
        Core memory enrichment logic.
        
        Args:
            ticket_id: Jira ticket ID
            feature_id: Feature identifier
            files_referenced: List of file names
        
        Returns:
            Memory enrichment data with related_nodes, connected_features, complexity_score
        """
        if self.backend != "fs":
            # Vector DB path would live here later
            return {
                "related_nodes": {},
                "connected_features": [],
                "complexity_score": None
            }
        
        # Create filesystem structure
        feature_dir = os.path.join(self.root, "features", feature_id, ticket_id)
        os.makedirs(feature_dir, exist_ok=True)
        
        # Create files.json
        files_json = {
            "files": [{"name": f, "size": None, "hash": None} for f in files_referenced],
            "created_at": time.time()
        }
        with open(os.path.join(feature_dir, "files.json"), "w") as f:
            json.dump(files_json, f, indent=2)
        
        # Create graph.json with heuristic relationships
        related_nodes = self._heuristic_links(files_referenced)
        connected_features = self._find_connected_features(feature_id, files_referenced)
        complexity_score = self._calculate_complexity(files_referenced)
        
        graph_json = {
            "related_nodes": related_nodes,
            "connected_features": connected_features,
            "complexity_score": complexity_score
        }
        with open(os.path.join(feature_dir, "graph.json"), "w") as f:
            json.dump(graph_json, f, indent=2)
        
        # Create summary.json
        summary_json = {
            "ticket_id": ticket_id,
            "feature_id": feature_id,
            "created_at": time.time()
        }
        with open(os.path.join(feature_dir, "summary.json"), "w") as f:
            json.dump(summary_json, f, indent=2)
        
        # Create embeddings.jsonl (stub for now)
        embeddings_file = os.path.join(feature_dir, "embeddings.jsonl")
        with open(embeddings_file, "w") as f:
            for file_name in files_referenced:
                embedding_entry = {
                    "file": file_name,
                    "text_hash": None,
                    "embedding": None  # Stub for MVP
                }
                f.write(json.dumps(embedding_entry) + "\n")
        
        # Create README.md for human context
        readme_content = f"""# {feature_id} - {ticket_id}

## Feature Overview
This directory contains synthetic memory for the {feature_id} feature implementation.

## Files Involved
{chr(10).join(f"- {f}" for f in files_referenced)}

## Complexity Score
{complexity_score:.2f}

## Connected Features
{', '.join(connected_features) if connected_features else 'None detected'}

## Related Nodes
{chr(10).join(f"- {k} ↔ {', '.join(v)}" for k, v in related_nodes.items()) if related_nodes else 'None detected'}

---
Generated by Jr Dev Agent v2 Synthetic Memory
"""
        with open(os.path.join(feature_dir, "README.md"), "w") as f:
            f.write(readme_content)
        
        # Return enrichment data
        return {
            "ticket_id": ticket_id,
            "prompt_version": None,
            "files_touched": files_referenced,
            "embedding_vector": None,  # Stub for FS MVP
            "complexity_score": complexity_score,
            "feature_id": feature_id,
            "related_nodes": related_nodes,
            "connected_features": connected_features,
            "dev_feedback": {"accepted": None, "edits_made": None, "retry_count": 0}
        }
    
    def _extract_files_from_ticket(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Extract file references from ticket data"""
        files = []
        
        # Try various fields where files might be mentioned
        if "files_affected" in ticket_data:
            if isinstance(ticket_data["files_affected"], list):
                files.extend(ticket_data["files_affected"])
            elif isinstance(ticket_data["files_affected"], str):
                files.extend([f.strip() for f in ticket_data["files_affected"].split(",")])
        
        # Look in description for file patterns
        description = ticket_data.get("description", "")
        if description:
            # Simple pattern matching for common file extensions
            import re
            file_patterns = r'\b[\w\-\.\/]+\.(?:ts|js|tsx|jsx|py|java|graphql|json|yml|yaml)\b'
            found_files = re.findall(file_patterns, description)
            files.extend(found_files)
        
        # Remove duplicates and normalize
        files = list(set(files))
        return [f for f in files if f.strip()]
    
    def _determine_feature_id(self, ticket_data: Dict[str, Any], files: List[str]) -> str:
        """Determine feature ID from ticket data and files"""
        # Try explicit feature field first
        if "feature" in ticket_data:
            return ticket_data["feature"]
        
        # Try to extract from summary or description
        summary = ticket_data.get("summary", "").lower()
        description = ticket_data.get("description", "").lower()
        text = f"{summary} {description}"
        
        # Common feature patterns
        if "shipping" in text:
            return "shipping_feature"
        if "resolver" in text and ("graphql" in text or any("resolver" in f for f in files)):
            return "graphql_feature" 
        if "schema" in text and any(".graphql" in f for f in files):
            return "schema_feature"
        if "config" in text:
            return "configuration_feature"
        
        # Default fallback
        return "new_feature"
    
    def _heuristic_links(self, files: List[str]) -> Dict:
        """Create heuristic relationships between files"""
        # Group files by directory and type
        dirs = {}
        for f in files:
            # Extract directory-like info from filename
            if "/" in f:
                dir_part = "/".join(f.split("/")[:-1])
            else:
                dir_part = "."
            dirs.setdefault(dir_part, []).append(f.split("/")[-1])
        
        related = {}
        for group in dirs.values():
            for f in group:
                related[f] = [x for x in group if x != f]
        
        # Add type-based relationships
        resolvers = [f for f in files if "resolver" in f.lower()]
        schemas = [f for f in files if f.endswith(".graphql")]
        tests = [f for f in files if "test" in f.lower()]
        
        # Link resolvers to schemas
        for resolver in resolvers:
            related.setdefault(resolver, []).extend(schemas)
        
        # Link tests to implementation files
        for test in tests:
            impl_files = [f for f in files if f not in tests and "test" not in f.lower()]
            related.setdefault(test, []).extend(impl_files)
        
        return related
    
    def _find_connected_features(self, current_feature: str, files: List[str]) -> List[str]:
        """Find connected features based on file patterns"""
        features = []
        
        # Extract features from file names
        for f in files:
            # Common patterns
            if "shipping" in f.lower():
                features.append("shipping")
            if "pfs" in f.lower():
                features.append("pfs")
            if "sla" in f.lower():
                features.append("sla")
            if "config" in f.lower():
                features.append("configuration")
            if "resolver" in f.lower():
                features.append("graphql_resolvers")
            if ".graphql" in f:
                features.append("graphql_schema")
        
        # Remove duplicates and current feature
        features = list(set(features))
        if current_feature in features:
            features.remove(current_feature)
        
        return features
    
    def _calculate_complexity(self, files: List[str]) -> float:
        """Calculate complexity score based on files"""
        # Simple heuristic: more files and certain patterns = higher complexity
        n = len(files)
        base_score = min(1.0, 0.3 + 0.1 * n)
        
        # Boost for certain file types
        multipliers = []
        if any("resolver" in f.lower() for f in files):
            multipliers.append(1.2)
        if any(".graphql" in f for f in files):
            multipliers.append(1.3)
        if any("config" in f.lower() for f in files):
            multipliers.append(1.1)
        if any("test" in f.lower() for f in files):
            multipliers.append(0.9)  # Tests reduce perceived complexity
        
        final_score = base_score
        for mult in multipliers:
            final_score *= mult
        
        return min(1.0, final_score)
    
    def get_feature_history(self, feature_id: str) -> Dict:
        """Get history of tickets for a feature (for debugging)"""
        feature_path = os.path.join(self.root, "features", feature_id)
        if not os.path.exists(feature_path):
            return {"tickets": []}
        
        tickets = []
        for ticket_dir in os.listdir(feature_path):
            ticket_path = os.path.join(feature_path, ticket_dir)
            if os.path.isdir(ticket_path):
                summary_file = os.path.join(ticket_path, "summary.json")
                if os.path.exists(summary_file):
                    with open(summary_file, "r") as f:
                        summary = json.load(f)
                        tickets.append(summary)
        
        return {"feature_id": feature_id, "tickets": tickets}
    
    async def record_completion(self, ticket_id: str, pr_url: str, pess_score: float, metadata: Dict = None):
        """
        Record completion of a ticket for future memory enhancement.
        
        Args:
            ticket_id: Jira ticket ID
            pr_url: Pull request URL
            pess_score: PESS score for the completion
            metadata: Additional completion metadata
        """
        try:
            # Find all memory locations for this ticket
            if os.path.exists(self.root):
                features_root = os.path.join(self.root, "features")
                if os.path.exists(features_root):
                    for feature_name in os.listdir(features_root):
                        ticket_dir = os.path.join(features_root, feature_name, ticket_id)
                        if os.path.exists(ticket_dir):
                            # Update agent_run.json
                            agent_run_data = {
                                "ticket_id": ticket_id,
                                "pr_url": pr_url,
                                "pess_score": pess_score,
                                "completion_timestamp": time.time(),
                                "metadata": metadata or {}
                            }
                            
                            agent_run_file = os.path.join(ticket_dir, "agent_run.json")
                            with open(agent_run_file, "w") as f:
                                json.dump(agent_run_data, f, indent=2)
                            
                            self.logger.info(f"Updated memory completion for {ticket_id} in feature {feature_name}")
                            
        except Exception as e:
            self.logger.error(f"Error recording completion for {ticket_id}: {str(e)}")
