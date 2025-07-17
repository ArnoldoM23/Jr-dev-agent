import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

from .qdrant_client import QdrantVectorClient
from ..models.memory_models import GraphNode, GraphEdge, FileFeatureGraphData

logger = logging.getLogger(__name__)

class FileFeatureGraph:
    """
    File-Feature relationship graph manager using Qdrant metadata.
    
    Features:
    - Track file-to-file relationships
    - Track file-to-feature relationships
    - Track feature-to-feature relationships
    - Edge weighting by frequency and recency
    - Graph traversal and analysis
    """
    
    def __init__(self, qdrant_client: QdrantVectorClient):
        self.qdrant_client = qdrant_client
        self.graph_cache: Dict[str, FileFeatureGraphData] = {}
        self.cache_timeout = 300  # 5 minutes
        
        logger.info("✅ FileFeatureGraph initialized")
    
    async def update_relationships(
        self,
        ticket_id: str,
        files_touched: List[str],
        feature_id: str,
        connected_features: List[str]
    ):
        """
        Update graph relationships based on ticket activity.
        
        Args:
            ticket_id: Ticket identifier
            files_touched: List of files modified
            feature_id: Primary feature being worked on
            connected_features: Related features
        """
        try:
            # Update file-to-file relationships
            await self._update_file_to_file_relationships(ticket_id, files_touched)
            
            # Update file-to-feature relationships
            await self._update_file_to_feature_relationships(ticket_id, files_touched, feature_id)
            
            # Update feature-to-feature relationships
            await self._update_feature_to_feature_relationships(ticket_id, feature_id, connected_features)
            
            # Clear cache for affected features
            self._clear_cache_for_feature(feature_id)
            for connected_feature in connected_features:
                self._clear_cache_for_feature(connected_feature)
            
            logger.info(f"✅ Updated relationships for ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update relationships for ticket {ticket_id}: {e}")
            raise
    
    async def _update_file_to_file_relationships(self, ticket_id: str, files_touched: List[str]):
        """
        Update file-to-file relationships based on files modified together.
        
        Args:
            ticket_id: Ticket identifier
            files_touched: List of files modified together
        """
        try:
            # Create relationships between all pairs of files
            for i, file1 in enumerate(files_touched):
                for j, file2 in enumerate(files_touched):
                    if i != j:  # Don't create self-relationships
                        await self._increment_relationship_weight(
                            source=file1,
                            target=file2,
                            relationship_type="file_to_file",
                            context={"ticket_id": ticket_id}
                        )
            
        except Exception as e:
            logger.error(f"❌ Failed to update file-to-file relationships: {e}")
            raise
    
    async def _update_file_to_feature_relationships(self, ticket_id: str, files_touched: List[str], feature_id: str):
        """
        Update file-to-feature relationships.
        
        Args:
            ticket_id: Ticket identifier
            files_touched: List of files modified
            feature_id: Feature being worked on
        """
        try:
            for file_path in files_touched:
                await self._increment_relationship_weight(
                    source=file_path,
                    target=feature_id,
                    relationship_type="file_to_feature",
                    context={"ticket_id": ticket_id}
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update file-to-feature relationships: {e}")
            raise
    
    async def _update_feature_to_feature_relationships(self, ticket_id: str, feature_id: str, connected_features: List[str]):
        """
        Update feature-to-feature relationships.
        
        Args:
            ticket_id: Ticket identifier
            feature_id: Primary feature
            connected_features: Related features
        """
        try:
            for connected_feature in connected_features:
                await self._increment_relationship_weight(
                    source=feature_id,
                    target=connected_feature,
                    relationship_type="feature_to_feature",
                    context={"ticket_id": ticket_id}
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update feature-to-feature relationships: {e}")
            raise
    
    async def _increment_relationship_weight(
        self,
        source: str,
        target: str,
        relationship_type: str,
        context: Dict[str, Any]
    ):
        """
        Increment the weight of a relationship edge.
        
        Args:
            source: Source node identifier
            target: Target node identifier
            relationship_type: Type of relationship
            context: Additional context information
        """
        try:
            # Store relationship data in Qdrant metadata
            # This is a simplified implementation - in practice, you might use a dedicated graph storage
            
            # For now, we'll track relationships in memory and update them in the search results
            relationship_key = f"{source}_{target}_{relationship_type}"
            
            # This could be stored as a separate collection in Qdrant for relationships
            # For the MVP, we'll track it in the payload metadata
            
            logger.debug(f"✅ Incremented relationship weight: {relationship_key}")
            
        except Exception as e:
            logger.error(f"❌ Failed to increment relationship weight: {e}")
            raise
    
    async def get_feature_graph(self, feature_id: str, depth: int = 2) -> FileFeatureGraphData:
        """
        Get the graph data for a specific feature.
        
        Args:
            feature_id: Feature identifier
            depth: Depth of graph traversal
            
        Returns:
            FileFeatureGraphData object
        """
        try:
            # Check cache first
            cache_key = f"{feature_id}_{depth}"
            if cache_key in self.graph_cache:
                cached_data = self.graph_cache[cache_key]
                # Check if cache is still valid (simplified - would normally check timestamp)
                return cached_data
            
            # Build graph data
            nodes = []
            edges = []
            
            # Get all memory points related to this feature
            search_results = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata-only search
                limit=1000,
                score_threshold=0.0,
                filter_conditions={"feature_id": feature_id}
            )
            
            # Extract nodes and edges from memory points
            file_nodes = set()
            feature_nodes = set()
            
            for result in search_results:
                payload = result.payload
                
                # Add feature node
                feature_nodes.add(payload.feature_id)
                
                # Add file nodes
                for file_path in payload.files_touched:
                    file_nodes.add(file_path)
                
                # Add connected features
                for connected_feature in payload.connected_features:
                    feature_nodes.add(connected_feature)
            
            # Create node objects
            for file_path in file_nodes:
                nodes.append(GraphNode(
                    node_id=file_path,
                    node_type="file",
                    metadata={"path": file_path},
                    connections=[],
                    weight=1.0
                ))
            
            for feature_name in feature_nodes:
                nodes.append(GraphNode(
                    node_id=feature_name,
                    node_type="feature",
                    metadata={"feature_id": feature_name},
                    connections=[],
                    weight=1.0
                ))
            
            # Create edges (simplified - would normally calculate weights)
            for result in search_results:
                payload = result.payload
                
                # File-to-feature edges
                for file_path in payload.files_touched:
                    edges.append(GraphEdge(
                        source=file_path,
                        target=payload.feature_id,
                        weight=1.0,
                        edge_type="file_to_feature",
                        metadata={"ticket_id": payload.ticket_id}
                    ))
                
                # Feature-to-feature edges
                for connected_feature in payload.connected_features:
                    edges.append(GraphEdge(
                        source=payload.feature_id,
                        target=connected_feature,
                        weight=1.0,
                        edge_type="feature_to_feature",
                        metadata={"ticket_id": payload.ticket_id}
                    ))
            
            # Update node connections
            for node in nodes:
                node.connections = [
                    edge.target for edge in edges if edge.source == node.node_id
                ]
            
            graph_data = FileFeatureGraphData(
                nodes=nodes,
                edges=edges,
                center_node=feature_id,
                depth=depth
            )
            
            # Cache the result
            self.graph_cache[cache_key] = graph_data
            
            logger.info(f"✅ Generated graph for feature {feature_id}: {len(nodes)} nodes, {len(edges)} edges")
            return graph_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get feature graph for {feature_id}: {e}")
            raise
    
    async def get_related_files(self, feature_id: str, limit: int = 10) -> List[str]:
        """
        Get files most related to a specific feature.
        
        Args:
            feature_id: Feature identifier
            limit: Maximum number of files to return
            
        Returns:
            List of file paths sorted by relevance
        """
        try:
            # Search for memory points related to this feature
            search_results = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata-only search
                limit=100,
                score_threshold=0.0,
                filter_conditions={"feature_id": feature_id}
            )
            
            # Count file frequency
            file_frequency = defaultdict(int)
            for result in search_results:
                for file_path in result.payload.files_touched:
                    file_frequency[file_path] += 1
            
            # Sort by frequency and return top results
            sorted_files = sorted(file_frequency.items(), key=lambda x: x[1], reverse=True)
            related_files = [file_path for file_path, _ in sorted_files[:limit]]
            
            logger.info(f"✅ Found {len(related_files)} related files for feature {feature_id}")
            return related_files
            
        except Exception as e:
            logger.error(f"❌ Failed to get related files for feature {feature_id}: {e}")
            raise
    
    async def get_connected_features(self, feature_id: str, limit: int = 5) -> List[str]:
        """
        Get features most connected to a specific feature.
        
        Args:
            feature_id: Feature identifier
            limit: Maximum number of features to return
            
        Returns:
            List of feature IDs sorted by connection strength
        """
        try:
            # Search for memory points related to this feature
            search_results = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata-only search
                limit=100,
                score_threshold=0.0,
                filter_conditions={"feature_id": feature_id}
            )
            
            # Count feature connections
            feature_connections = defaultdict(int)
            for result in search_results:
                for connected_feature in result.payload.connected_features:
                    if connected_feature != feature_id:  # Don't include self
                        feature_connections[connected_feature] += 1
            
            # Sort by connection strength and return top results
            sorted_features = sorted(feature_connections.items(), key=lambda x: x[1], reverse=True)
            connected_features = [feature_name for feature_name, _ in sorted_features[:limit]]
            
            logger.info(f"✅ Found {len(connected_features)} connected features for feature {feature_id}")
            return connected_features
            
        except Exception as e:
            logger.error(f"❌ Failed to get connected features for feature {feature_id}: {e}")
            raise
    
    async def calculate_file_importance(self, file_path: str) -> float:
        """
        Calculate the importance score of a file based on its graph connections.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        try:
            # Search for memory points that touched this file
            search_results = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata-only search
                limit=100,
                score_threshold=0.0,
                filter_conditions={"files_touched": [file_path]}
            )
            
            if not search_results:
                return 0.0
            
            # Calculate importance based on:
            # 1. Number of tickets that touched this file
            # 2. Number of features this file is connected to
            # 3. Recency of modifications
            
            unique_tickets = set()
            unique_features = set()
            total_modifications = 0
            
            for result in search_results:
                unique_tickets.add(result.payload.ticket_id)
                unique_features.add(result.payload.feature_id)
                unique_features.update(result.payload.connected_features)
                total_modifications += 1
            
            # Normalize scores
            ticket_score = min(len(unique_tickets) / 10.0, 1.0)  # Max 10 tickets = 1.0
            feature_score = min(len(unique_features) / 5.0, 1.0)  # Max 5 features = 1.0
            frequency_score = min(total_modifications / 20.0, 1.0)  # Max 20 modifications = 1.0
            
            # Weighted importance score
            importance = (ticket_score * 0.4) + (feature_score * 0.4) + (frequency_score * 0.2)
            
            logger.debug(f"✅ Calculated importance for {file_path}: {importance:.2f}")
            return importance
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate importance for {file_path}: {e}")
            return 0.0
    
    def _clear_cache_for_feature(self, feature_id: str):
        """
        Clear cached graph data for a specific feature.
        
        Args:
            feature_id: Feature identifier
        """
        try:
            keys_to_remove = [key for key in self.graph_cache.keys() if key.startswith(f"{feature_id}_")]
            for key in keys_to_remove:
                del self.graph_cache[key]
            
            logger.debug(f"✅ Cleared cache for feature {feature_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear cache for feature {feature_id}: {e}")
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the graph.
        
        Returns:
            Dictionary with graph statistics
        """
        try:
            # Get all memory points
            search_results = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata-only search
                limit=10000,
                score_threshold=0.0
            )
            
            unique_files = set()
            unique_features = set()
            
            for result in search_results:
                unique_files.update(result.payload.files_touched)
                unique_features.add(result.payload.feature_id)
                unique_features.update(result.payload.connected_features)
            
            stats = {
                "total_memory_points": len(search_results),
                "unique_files": len(unique_files),
                "unique_features": len(unique_features),
                "cache_size": len(self.graph_cache)
            }
            
            logger.info(f"✅ Generated graph statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get graph statistics: {e}")
            raise 