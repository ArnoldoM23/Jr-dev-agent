import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, SearchParams
)
import openai
from openai import OpenAI

from .core.embedding_engine import EmbeddingEngine
from .core.qdrant_client import QdrantVectorClient
from .core.graph_manager import FileFeatureGraph
from .core.context_enricher import ContextEnricher
from .core.complexity_scorer import ComplexityScorer
from .models.memory_models import (
    MemoryPoint, MemoryPayload, ContextEnrichmentRequest,
    ContextEnrichmentResponse, ComplexityScoreRequest,
    ComplexityScoreResponse, MemoryStoreRequest, MemoryStoreResponse,
    MemorySearchRequest, MemorySearchResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Jr Dev Agent - Synthetic Memory System",
    description="Long-term contextual understanding and architectural memory",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
embedding_engine: Optional[EmbeddingEngine] = None
qdrant_client: Optional[QdrantVectorClient] = None
graph_manager: Optional[FileFeatureGraph] = None
context_enricher: Optional[ContextEnricher] = None
complexity_scorer: Optional[ComplexityScorer] = None

@app.on_event("startup")
async def startup_event():
    """Initialize all service components on startup"""
    global embedding_engine, qdrant_client, graph_manager, context_enricher, complexity_scorer
    
    try:
        logger.info("🚀 Starting Synthetic Memory System...")
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize embedding engine
        embedding_engine = EmbeddingEngine(openai_client)
        logger.info("✅ Embedding engine initialized")
        
        # Initialize Qdrant client
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "jrdev_memory")
        
        qdrant_client = QdrantVectorClient(
            host=qdrant_host,
            port=qdrant_port,
            collection_name=collection_name
        )
        await qdrant_client.initialize()
        logger.info("✅ Qdrant client initialized")
        
        # Initialize graph manager
        graph_manager = FileFeatureGraph(qdrant_client)
        logger.info("✅ Graph manager initialized")
        
        # Initialize context enricher
        context_enricher = ContextEnricher(
            qdrant_client=qdrant_client,
            embedding_engine=embedding_engine,
            graph_manager=graph_manager
        )
        logger.info("✅ Context enricher initialized")
        
        # Initialize complexity scorer
        complexity_scorer = ComplexityScorer(qdrant_client)
        logger.info("✅ Complexity scorer initialized")
        
        logger.info("🎉 Synthetic Memory System started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start Synthetic Memory System: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "synthetic-memory",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "embedding_engine": embedding_engine is not None,
            "qdrant_client": qdrant_client is not None,
            "graph_manager": graph_manager is not None,
            "context_enricher": context_enricher is not None,
            "complexity_scorer": complexity_scorer is not None
        }
    }

@app.post("/memory/store", response_model=MemoryStoreResponse)
async def store_memory(request: MemoryStoreRequest):
    """Store embeddings with metadata in Qdrant"""
    try:
        if not qdrant_client or not embedding_engine:
            raise HTTPException(status_code=500, detail="Service not initialized")
        
        # Generate embedding for the prompt text
        embedding = await embedding_engine.generate_embedding(request.prompt_text)
        
        # Create memory payload
        payload = MemoryPayload(
            ticket_id=request.ticket_id,
            template_name=request.template_name,
            prompt_version=request.prompt_version,
            files_touched=request.files_touched,
            feature_id=request.feature_id,
            connected_features=request.connected_features or [],
            complexity_score=request.complexity_score,
            related_nodes=request.related_nodes or {},
            retry_count=request.retry_count,
            dev_feedback=request.dev_feedback,
            snapshot_id=request.snapshot_id,
            created_at=datetime.utcnow()
        )
        
        # Store in Qdrant
        point_id = f"{request.ticket_id}_run_{request.run_id}"
        await qdrant_client.upsert_point(
            point_id=point_id,
            vector=embedding,
            payload=payload.dict()
        )
        
        # Update graph relationships
        if graph_manager:
            await graph_manager.update_relationships(
                ticket_id=request.ticket_id,
                files_touched=request.files_touched,
                feature_id=request.feature_id,
                connected_features=request.connected_features or []
            )
        
        logger.info(f"✅ Stored memory for ticket {request.ticket_id}")
        
        return MemoryStoreResponse(
            success=True,
            point_id=point_id,
            embedding_dimensions=len(embedding),
            message="Memory stored successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")

@app.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """Perform semantic search in memory"""
    try:
        if not qdrant_client or not embedding_engine:
            raise HTTPException(status_code=500, detail="Service not initialized")
        
        # Generate embedding for search query
        query_embedding = await embedding_engine.generate_embedding(request.query_text)
        
        # Perform search
        search_results = await qdrant_client.search(
            query_vector=query_embedding,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filter_conditions=request.filter_conditions
        )
        
        logger.info(f"✅ Search completed, found {len(search_results)} results")
        
        return MemorySearchResponse(
            success=True,
            results=search_results,
            total_results=len(search_results)
        )
        
    except Exception as e:
        logger.error(f"❌ Memory search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")

@app.post("/memory/enrich", response_model=ContextEnrichmentResponse)
async def enrich_context(request: ContextEnrichmentRequest):
    """Provide context enrichment for prompt generation"""
    try:
        if not context_enricher:
            raise HTTPException(status_code=500, detail="Context enricher not initialized")
        
        # Perform context enrichment
        enrichment_result = await context_enricher.enrich_prompt_context(
            ticket_id=request.ticket_id,
            prompt_text=request.prompt_text,
            files_mentioned=request.files_mentioned,
            feature_context=request.feature_context
        )
        
        logger.info(f"✅ Context enriched for ticket {request.ticket_id}")
        
        return enrichment_result
        
    except Exception as e:
        logger.error(f"❌ Context enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context enrichment failed: {str(e)}")

@app.post("/memory/complexity", response_model=ComplexityScoreResponse)
async def calculate_complexity(request: ComplexityScoreRequest):
    """Calculate complexity score for a task"""
    try:
        if not complexity_scorer:
            raise HTTPException(status_code=500, detail="Complexity scorer not initialized")
        
        # Calculate complexity score
        complexity_result = await complexity_scorer.calculate_complexity(
            ticket_id=request.ticket_id,
            retry_count=request.retry_count,
            features_referenced=request.features_referenced,
            lines_of_code=request.lines_of_code,
            dev_feedback=request.dev_feedback,
            historical_context=request.historical_context
        )
        
        logger.info(f"✅ Complexity calculated for ticket {request.ticket_id}")
        
        return complexity_result
        
    except Exception as e:
        logger.error(f"❌ Complexity calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Complexity calculation failed: {str(e)}")

@app.get("/memory/graph/{feature_id}")
async def get_feature_graph(feature_id: str):
    """Get file-feature relationship graph"""
    try:
        if not graph_manager:
            raise HTTPException(status_code=500, detail="Graph manager not initialized")
        
        graph_data = await graph_manager.get_feature_graph(feature_id)
        
        return {
            "success": True,
            "feature_id": feature_id,
            "graph_data": graph_data
        }
        
    except Exception as e:
        logger.error(f"❌ Graph retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph retrieval failed: {str(e)}")

@app.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        if not qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        
        stats = await qdrant_client.get_collection_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.delete("/memory/cleanup")
async def cleanup_memory():
    """Cleanup old memory entries"""
    try:
        if not qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        
        cleanup_result = await qdrant_client.cleanup_old_entries()
        
        return {
            "success": True,
            "cleanup_result": cleanup_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Memory cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Memory cleanup failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    ) 