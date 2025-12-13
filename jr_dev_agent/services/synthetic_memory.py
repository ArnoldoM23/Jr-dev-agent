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
                    # Only override root if it wasn't explicitly set in __init__ (default is "syntheticMemory")
                    # or if we want config to take precedence over default but not over explicit override.
                    # Simpler check: if self.root is still the default, use config.
                    config_root = memory_config.get("fs", {}).get("root_dir")
                    if config_root and self.root == "syntheticMemory":
                        self.root = config_root
        except FileNotFoundError:
            pass  # Use defaults
            
        # Ensure root directory exists
        os.makedirs(self.root, exist_ok=True)
        
        self.initialized = True
        self.logger.info(f"Synthetic Memory initialized (backend: {self.backend}, root: {self.root})")
    
    async def enrich_context(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ticket context with synthetic memory using the 5-step retrieval algorithm.
        
        This implements Layer 1 - MCP "Memory Enrichment" as specified:
        1. Identify feature scope
        2. Locate memory packs  
        3. Score & select
        4. Assemble MemoryEnvelope
        5. Return enriched context
        
        Args:
            ticket_data: Raw ticket data from Jira
            
        Returns:
            Enhanced context with MemoryEnvelope data
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            ticket_id = ticket_data.get("ticket_id", "unknown")
            
            # Step 1: Identify feature scope
            feature_id, files_referenced = self._identify_feature_scope(ticket_data)
            
            # ENHANCEMENT: Create memory for current ticket (preserving original logic)
            current_memory = await self._enrich_memory(ticket_id, feature_id, files_referenced)
            self.logger.info(f"Created memory structures for current ticket {ticket_id}")
            
            # Step 2: Locate memory packs (for context from prior runs)
            memory_packs = self._locate_memory_packs(feature_id)
            
            # Step 3: Score & select relevant runs
            relevant_runs = self._score_and_select(memory_packs, files_referenced, ticket_data)
            
            # Step 4: Assemble MemoryEnvelope (enhancement for context enrichment)
            memory_envelope = self._assemble_memory_envelope(feature_id, relevant_runs, files_referenced, ticket_data)
            
            # Step 5: Return enriched context combining original + enhanced logic
            return {
                "context_enriched": True,
                "enrichment_timestamp": time.time(),
                "current_memory": current_memory,  # Original memory creation result
                "memory_envelope": memory_envelope,  # Enhanced context retrieval
                "complexity_score": memory_envelope.get("complexity_score", current_memory.get("complexity_score", 0.5)),
                "related_files": memory_envelope.get("related_nodes", current_memory.get("related_nodes", {})),
                "connected_features": memory_envelope.get("connected_features", current_memory.get("connected_features", []))
            }
            
        except Exception as e:
            self.logger.error(f"Error enriching context for {ticket_data.get('ticket_id')}: {str(e)}")
            
            # Try to at least create memory for current ticket (preserve original functionality)
            ticket_id = ticket_data.get("ticket_id", "unknown")
            try:
                feature_id, files_referenced = self._identify_feature_scope(ticket_data)
                current_memory = await self._enrich_memory(ticket_id, feature_id, files_referenced)
                self.logger.info(f"Created basic memory structures for {ticket_id} despite enrichment error")
            except:
                current_memory = {"related_nodes": {}, "connected_features": [], "complexity_score": 0.5}
            
            # Return minimal enrichment with empty MemoryEnvelope but preserve current memory creation
            return {
                "context_enriched": False,
                "error": str(e),
                "enrichment_timestamp": time.time(),
                "current_memory": current_memory,  # Still try to create memory for current ticket
                "memory_envelope": {
                    "feature_id": "unknown",
                    "related_nodes": {},
                    "connected_features": [],
                    "prior_runs": [],
                    "file_hints": [],
                    "complexity_score": 0.5
                },
                "complexity_score": current_memory.get("complexity_score", 0.5),
                "related_files": current_memory.get("related_nodes", {}),
                "connected_features": current_memory.get("connected_features", [])
            }
    
    def _identify_feature_scope(self, ticket_data: Dict[str, Any]) -> tuple[str, List[str]]:
        """
        Step 1: Identify feature scope
        
        Prefer explicit feature_id in metadata, else infer from ticket/title + files
        using directory overlap heuristic.
        
        Returns:
            tuple: (feature_id, files_referenced)
        """
        # Extract files from ticket data
        files_referenced = self._extract_files_from_ticket(ticket_data)
        
        # Prefer explicit feature_id from top-level payload or PromptBuilder metadata
        if 'feature_id' in ticket_data and ticket_data['feature_id']:
            feature_id = ticket_data['feature_id']
        elif 'metadata' in ticket_data and 'feature_id' in ticket_data['metadata']:
            feature_id = ticket_data['metadata']['feature_id']
        else:
            # Infer from ticket data using existing logic  
            feature_id = self._determine_feature_id(ticket_data, files_referenced)
            
        return feature_id, files_referenced
    
    def _locate_memory_packs(self, feature_id: str) -> List[Dict]:
        """
        Step 2: Locate memory packs
        
        Read syntheticMemory/features/<feature_id>/**/{summary.json,graph.json,files.json,agent_run.json}
        
        Returns:
            List of memory packs with loaded data
        """
        memory_packs = []
        
        if self.backend != "fs":
            return memory_packs
            
        feature_path = Path(self.root) / "features" / feature_id
        
        if not feature_path.exists():
            self.logger.info(f"No memory packs found for feature: {feature_id}")
            return memory_packs
            
        # Find all ticket directories under this feature
        try:
            for ticket_dir in feature_path.iterdir():
                if ticket_dir.is_dir():
                    pack = self._load_memory_pack(ticket_dir)
                    if pack:
                        memory_packs.append(pack)
        except Exception as e:
            self.logger.warning(f"Error scanning memory packs for {feature_id}: {str(e)}")
            
        return memory_packs
    
    def _load_memory_pack(self, ticket_dir: Path) -> Dict:
        """
        Load a complete memory pack from a ticket directory.
        
        Returns:
            Memory pack with summary, graph, files, and agent_run data
        """
        pack = {
            "ticket_id": ticket_dir.name,
            "directory": str(ticket_dir)
        }
        
        # Load each file if it exists
        for filename in ["graph.json", "files.json", "agent_run.json"]:
            file_path = ticket_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        pack[filename.replace('.json', '')] = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error loading {filename} from {ticket_dir}: {str(e)}")
                    
        return pack if len(pack) > 2 else None  # Must have more than just ticket_id and directory
    
    def _score_and_select(self, memory_packs: List[Dict], files_referenced: List[str], ticket_data: Dict) -> List[Dict]:
        """
        Step 3: Score & select relevant runs
        
        Pick last N relevant runs (recent + overlapping files).
        Compute relevance score: w1*file_overlap + w2*recency + w3*same_template_type
        
        Returns:
            List of scored and selected relevant runs
        """
        if not memory_packs:
            return []
            
        scored_runs = []
        template_type = ticket_data.get('template_name', 'unknown')
        current_time = time.time()
        
        for pack in memory_packs:
            score = self._calculate_relevance_score(pack, files_referenced, template_type, current_time)
            if score > 0:  # Only include relevant runs
                # Extract file names from pack files
                pack_files = pack.get("files", {}).get("files", [])
                files_list = [f.get("name", str(f)) if isinstance(f, dict) else str(f) for f in pack_files]
                
                run_data = {
                    "ticket_id": pack["ticket_id"],
                    "score": score,
                    "files_touched": files_list,
                    "result": pack.get("agent_run", {}).get("result", "unknown"),
                    "pr_url": pack.get("agent_run", {}).get("pr_url"),
                    "pess_score": pack.get("agent_run", {}).get("pess_score"),
                    "related_nodes": pack.get("graph", {}).get("related_nodes", {}),
                    "connected_features": pack.get("graph", {}).get("connected_features", []),
                    "complexity_score": pack.get("graph", {}).get("complexity_score", 0.5)
                }
                scored_runs.append(run_data)
        
        # Sort by score (descending) and return top N (default 5)
        scored_runs.sort(key=lambda x: x["score"], reverse=True)
        return scored_runs[:5]
    
    def _calculate_relevance_score(self, pack: Dict, files_referenced: List[str], template_type: str, current_time: float) -> float:
        """
        Calculate relevance score using: w1*file_overlap + w2*recency + w3*same_template_type
        
        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Extract pack files
        pack_files = []
        if "files" in pack and "files" in pack["files"]:
            pack_files = [f.get("name", "") if isinstance(f, dict) else str(f) for f in pack["files"]["files"]]
        
        # Calculate file overlap (w1 = 0.5)
        if files_referenced and pack_files:
            overlap = len(set(files_referenced) & set(pack_files))
            max_files = max(len(files_referenced), len(pack_files))
            file_overlap_score = overlap / max_files if max_files > 0 else 0
        else:
            file_overlap_score = 0
            
        # Calculate recency (w2 = 0.3) - based on agent_run timestamp if available
        recency_score = 0
        if "agent_run" in pack and "completion_timestamp" in pack["agent_run"]:
            try:
                run_time = float(pack["agent_run"]["completion_timestamp"])
                # Decay over 30 days (2592000 seconds)
                days_old = (current_time - run_time) / 86400  # seconds to days
                recency_score = max(0, 1 - (days_old / 30))
            except (ValueError, TypeError):
                pass
                
        # Calculate template type match (w3 = 0.2)
        template_score = 0
        # Check agent_run for template info (was in summary)
        # Note: We didn't explicitly store template_name in agent_run in previous steps,
        # but the ticket_data passed to _score_and_select has it.
        # If we want to match against historical runs, we rely on what's in the pack.
        # Since we removed summary.json, we should check agent_run.
        # But we haven't stored template_name in agent_run yet.
        # For now, let's check agent_run if it has it, or just skip this part if data missing.
        if "agent_run" in pack and pack["agent_run"].get("template_name") == template_type:
            template_score = 1.0
        # Fallback to summary if it still exists (legacy data)
        elif "summary" in pack and pack["summary"].get("template_name") == template_type:
            template_score = 1.0
            
        # Weighted combination
        relevance_score = (0.5 * file_overlap_score) + (0.3 * recency_score) + (0.2 * template_score)
        return min(1.0, relevance_score)
    
    def _assemble_memory_envelope(self, feature_id: str, relevant_runs: List[Dict], files_referenced: List[str], ticket_data: Dict) -> Dict:
        """
        Step 4: Assemble MemoryEnvelope
        
        Creates the MemoryEnvelope structure as specified in the requirements.
        
        Returns:
            MemoryEnvelope dict with all required fields
        """
        # Aggregate related nodes from all relevant runs
        related_nodes = {}
        connected_features = set()
        complexity_scores = []
        
        for run in relevant_runs:
            # Merge related nodes
            if run.get("related_nodes"):
                for node, connections in run["related_nodes"].items():
                    if node not in related_nodes:
                        related_nodes[node] = []
                    related_nodes[node].extend(connections)
                    
            # Collect connected features
            if run.get("connected_features"):
                connected_features.update(run["connected_features"])
                
            # Collect complexity scores
            if run.get("complexity_score"):
                complexity_scores.append(run["complexity_score"])
        
        # Deduplicate related_nodes connections
        for node in related_nodes:
            related_nodes[node] = list(set(related_nodes[node]))
        
        # Calculate aggregate complexity score
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.5
        
        # Generate file hints based on files and prior runs
        file_hints = self._generate_file_hints(files_referenced, relevant_runs)
        
        # Format prior runs for the envelope
        prior_runs = []
        for run in relevant_runs:
            prior_run = {
                "ticket_id": run["ticket_id"], 
                "pr_url": run.get("pr_url"),
                "files_touched": run.get("files_touched", []),
                "result": run.get("result", "unknown"),
                "score": run.get("pess_score", run.get("score", 0))
            }
            prior_runs.append(prior_run)
        
        return {
            "feature_id": feature_id,
            "related_nodes": related_nodes,
            "connected_features": list(connected_features),
            "prior_runs": prior_runs,
            "file_hints": file_hints,
            "complexity_score": round(avg_complexity, 2)
        }
    
    def _generate_file_hints(self, files_referenced: List[str], relevant_runs: List[Dict]) -> List[Dict]:
        """
        Generate file hints based on files and prior run patterns.
        
        Returns:
            List of file hints with path and note
        """
        file_hints = []
        
        # Group files by common patterns from prior runs
        ccm_files = [f for f in files_referenced if "setup-runtime-config" in f or "ccm" in f.lower()]
        resolver_files = [f for f in files_referenced if "resolver" in f.lower()]
        test_files = [f for f in files_referenced if "test" in f.lower()]
        
        # Generate hints based on file types and prior run learnings
        for ccm_file in ccm_files:
            file_hints.append({
                "path": ccm_file,
                "note": "CCM pattern lives here; do not modify unrelated flags."
            })
            
        for resolver_file in resolver_files:
            file_hints.append({
                "path": resolver_file, 
                "note": "GraphQL resolver - maintain existing patterns and add feature flag guards."
            })
            
        for test_file in test_files:
            file_hints.append({
                "path": test_file,
                "note": "Add test coverage for new functionality with CCM flag variations."
            })
            
        # Add hints from prior run patterns
        for run in relevant_runs:
            if run.get("result") == "merged" and run.get("files_touched"):
                for touched_file in run["files_touched"]:
                    if touched_file in files_referenced:
                        file_hints.append({
                            "path": touched_file,
                            "note": f"Previously modified in {run['ticket_id']} (merged successfully)"
                        })
        
        # Deduplicate hints by path
        seen_paths = set()
        unique_hints = []
        for hint in file_hints:
            if hint["path"] not in seen_paths:
                unique_hints.append(hint)
                seen_paths.add(hint["path"])
                
        return unique_hints
    
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
        
        # Create agent_run.json (initial)
        agent_run_json = {
            "ticket_id": ticket_id,
            "feature_id": feature_id,
            "created_at": time.time(),
            "status": "started"
        }
        with open(os.path.join(feature_dir, "agent_run.json"), "w") as f:
            json.dump(agent_run_json, f, indent=2)
        
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
    
    async def record_completion(self, ticket_id: str, pr_url: str, pess_score: float, metadata: Dict = None, 
                              changes_made: str = None, change_required: str = None, full_prompt: str = None):
        """
        Record completion of a ticket for future memory enhancement.
        
        Args:
            ticket_id: Jira ticket ID
            pr_url: Pull request URL
            pess_score: PESS score for the completion
            metadata: Additional completion metadata
            changes_made: Summary of changes made (from LLM)
            change_required: Summary of task requirements (from LLM)
            full_prompt: The full prompt used for the task
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
                            agent_run_file = os.path.join(ticket_dir, "agent_run.json")
                            existing_run_data = {}
                            if os.path.exists(agent_run_file):
                                try:
                                    with open(agent_run_file, 'r') as f:
                                        existing_run_data = json.load(f)
                                except Exception:
                                    pass

                            agent_run_data = {
                                "ticket_id": ticket_id,
                                "feature_id": feature_name,
                                "created_at": existing_run_data.get("created_at", time.time()),
                                "pr_url": pr_url or existing_run_data.get("pr_url"),
                                "pess_score": pess_score,
                                "completion_timestamp": time.time(),
                                "full_prompt": full_prompt or existing_run_data.get("full_prompt"),
                                "change_required": change_required or existing_run_data.get("change_required"),
                                "changes_made": changes_made or existing_run_data.get("changes_made"),
                                "metadata": metadata or {},
                                "status": "completed"
                            }
                            
                            with open(agent_run_file, "w") as f:
                                json.dump(agent_run_data, f, indent=2)

                            # Clean up old summary.json if it exists
                            summary_file = os.path.join(ticket_dir, "summary.json")
                            if os.path.exists(summary_file):
                                try:
                                    os.remove(summary_file)
                                    self.logger.info(f"Removed deprecated summary.json for {ticket_id}")
                                except Exception as e:
                                    self.logger.warning(f"Could not remove summary.json: {e}")
                            
                            self.logger.info(f"Updated memory completion for {ticket_id} in feature {feature_name}")
                            
        except Exception as e:
            self.logger.error(f"Error recording completion for {ticket_id}: {str(e)}")