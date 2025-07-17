from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from uuid import uuid4

class MemoryPayload(BaseModel):
    """Pydantic model for memory payload stored in Qdrant"""
    ticket_id: str
    template_name: str
    prompt_version: str
    files_touched: List[str]
    feature_id: str
    connected_features: List[str] = []
    complexity_score: float = Field(ge=0.0, le=1.0)
    related_nodes: Dict[str, List[str]] = {}
    retry_count: int = 0
    dev_feedback: Optional[Dict[str, Any]] = None
    snapshot_id: str
    created_at: datetime

class MemoryPoint(BaseModel):
    """Pydantic model for a complete memory point"""
    point_id: str
    vector: List[float]
    payload: MemoryPayload
    score: Optional[float] = None

class MemoryStoreRequest(BaseModel):
    """Request model for storing memory"""
    ticket_id: str
    run_id: str
    prompt_text: str
    template_name: str
    prompt_version: str
    files_touched: List[str]
    feature_id: str
    connected_features: Optional[List[str]] = None
    complexity_score: float = Field(ge=0.0, le=1.0)
    related_nodes: Optional[Dict[str, List[str]]] = None
    retry_count: int = 0
    dev_feedback: Optional[Dict[str, Any]] = None
    snapshot_id: str = Field(default_factory=lambda: f"snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")

class MemoryStoreResponse(BaseModel):
    """Response model for storing memory"""
    success: bool
    point_id: str
    embedding_dimensions: int
    message: str

class MemorySearchRequest(BaseModel):
    """Request model for searching memory"""
    query_text: str
    limit: int = 10
    score_threshold: float = 0.7
    filter_conditions: Optional[Dict[str, Any]] = None

class MemorySearchResponse(BaseModel):
    """Response model for searching memory"""
    success: bool
    results: List[MemoryPoint]
    total_results: int

class ContextEnrichmentRequest(BaseModel):
    """Request model for context enrichment"""
    ticket_id: str
    prompt_text: str
    files_mentioned: List[str] = []
    feature_context: Optional[str] = None

class ContextEnrichmentResponse(BaseModel):
    """Response model for context enrichment"""
    success: bool
    enriched_context: str
    related_files: List[str]
    connected_features: List[str]
    complexity_indicators: Dict[str, Any]
    retry_recommendations: List[str]
    top_3_reused_files: List[str]

class ComplexityScoreRequest(BaseModel):
    """Request model for complexity scoring"""
    ticket_id: str
    retry_count: int = 0
    features_referenced: List[str] = []
    lines_of_code: int = 0
    dev_feedback: Optional[Dict[str, Any]] = None
    historical_context: Optional[Dict[str, Any]] = None

class ComplexityScoreResponse(BaseModel):
    """Response model for complexity scoring"""
    success: bool
    complexity_score: float = Field(ge=0.0, le=1.0)
    score_components: Dict[str, float]
    factors: List[str]
    recommendations: List[str]

class GraphNode(BaseModel):
    """Graph node model"""
    node_id: str
    node_type: str  # 'file' or 'feature'
    metadata: Dict[str, Any]
    connections: List[str]
    weight: float = 1.0

class GraphEdge(BaseModel):
    """Graph edge model"""
    source: str
    target: str
    weight: float = 1.0
    edge_type: str  # 'file_to_file', 'file_to_feature', 'feature_to_feature'
    metadata: Dict[str, Any] = {}

class FileFeatureGraphData(BaseModel):
    """Complete graph data model"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    center_node: str
    depth: int = 2

class EmbeddingRequest(BaseModel):
    """Request model for embedding generation"""
    text: str
    model: str = "text-embedding-3-small"

class EmbeddingResponse(BaseModel):
    """Response model for embedding generation"""
    embedding: List[float]
    dimensions: int
    model_used: str
    tokens_used: int

class SnapshotMetadata(BaseModel):
    """Snapshot metadata model"""
    snapshot_id: str
    created_at: datetime
    ticket_ids: List[str]
    total_points: int
    version: str = "1.0"

class MemoryAnalytics(BaseModel):
    """Memory analytics model"""
    total_memories: int
    unique_tickets: int
    unique_features: int
    average_complexity: float
    retry_distribution: Dict[str, int]
    feature_frequency: Dict[str, int]
    recent_activity: List[Dict[str, Any]] 