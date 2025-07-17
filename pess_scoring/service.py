"""
PESS Scoring Service

FastAPI service for the Prompt Effectiveness Scoring System (PESS).
Provides REST API endpoints for scoring, feedback, and analytics.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import uvicorn

from .models.scoring_models import (
    ScoringInput, ScoringOutput, FeedbackData, AnalyticsRequest, AnalyticsResponse,
    TemplatePerformance, ScoreHistory, TaskType, FeedbackType
)
from .models.database_models import Base, ScoreRecord, FeedbackRecord, TemplateRecord, SessionRecord
from .core.pipeline import ScoringPipeline
from .core.scoring_algorithm import ScoringAlgorithm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pess_user:pess_password@localhost:5432/pess_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global pipeline instance
scoring_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global scoring_pipeline
    
    logger.info("Starting PESS Scoring Service")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize scoring pipeline
    db_session = SessionLocal()
    scoring_pipeline = ScoringPipeline(db_session)
    
    logger.info("PESS Scoring Service started successfully")
    yield
    
    # Cleanup
    db_session.close()
    logger.info("PESS Scoring Service stopped")

# FastAPI app
app = FastAPI(
    title="PESS - Prompt Effectiveness Scoring System",
    description="AI-powered scoring system for evaluating prompt effectiveness with 8-dimensional analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for database session
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PESS Scoring System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# Scoring endpoints
@app.post("/api/v1/score", response_model=Dict[str, Any], tags=["Scoring"])
async def score_prompt(
    source: str,
    input_data: Dict[str, Any],
    feedback_data: Optional[List[FeedbackData]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Score a prompt using the 5-stage PESS pipeline
    
    Args:
        source: Source of the request ('promptbuilder', 'mcp', 'vscode_extension', 'manual')
        input_data: Raw input data for scoring
        feedback_data: Optional feedback data for enhanced scoring
    
    Returns:
        Scoring pipeline result
    """
    try:
        logger.info(f"Scoring request received from {source}")
        
        # Process scoring request
        result = scoring_pipeline.process_scoring_request(source, input_data, feedback_data)
        
        if result['success']:
            logger.info(f"Scoring completed successfully: {result['final_score']:.2f}")
            return {
                "success": True,
                "session_id": result['session_id'],
                "final_score": result['final_score'],
                "processing_time": result['processing_time'],
                "stages_completed": result['stages_completed'],
                "scoring_output": result.get('scoring_output', {}).dict() if result.get('scoring_output') else None
            }
        else:
            logger.error(f"Scoring failed: {result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": result['errors'], "stages_completed": result['stages_completed']}
            )
            
    except Exception as e:
        logger.error(f"Scoring endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/score/batch", response_model=List[Dict[str, Any]], tags=["Scoring"])
async def batch_score_prompts(
    requests: List[Dict[str, Any]],
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Batch score multiple prompts
    
    Args:
        requests: List of scoring requests with format:
                 [{"source": str, "input_data": dict, "feedback_data": list}]
    
    Returns:
        List of scoring results
    """
    try:
        logger.info(f"Batch scoring request received for {len(requests)} requests")
        
        # Convert requests to pipeline format
        pipeline_requests = []
        for req in requests:
            source = req.get('source', 'manual')
            input_data = req.get('input_data', {})
            feedback_data = req.get('feedback_data', [])
            
            # Convert feedback data to FeedbackData objects
            feedback_objects = []
            for fb in feedback_data:
                feedback_objects.append(FeedbackData(**fb))
            
            pipeline_requests.append((source, input_data, feedback_objects))
        
        # Process batch
        results = scoring_pipeline.batch_process_scoring_requests(pipeline_requests)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_result = {
                "success": result['success'],
                "session_id": result['session_id'],
                "final_score": result.get('final_score'),
                "processing_time": result.get('processing_time', 0.0),
                "stages_completed": result.get('stages_completed', []),
                "errors": result.get('errors', [])
            }
            formatted_results.append(formatted_result)
        
        logger.info(f"Batch scoring completed for {len(formatted_results)} requests")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Batch scoring endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# Feedback endpoints
@app.post("/api/v1/feedback", response_model=Dict[str, Any], tags=["Feedback"])
async def submit_feedback(
    feedback_data: FeedbackData,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a scoring session
    
    Args:
        feedback_data: Feedback data object
        db: Database session
    
    Returns:
        Feedback submission result
    """
    try:
        logger.info(f"Feedback submitted for session {feedback_data.session_id}")
        
        # Save feedback to database
        feedback_record = FeedbackRecord(
            feedback_id=feedback_data.feedback_id,
            scoring_id=feedback_data.scoring_id,
            session_id=feedback_data.session_id,
            feedback_type=feedback_data.feedback_type.value,
            rating=feedback_data.rating,
            comment=feedback_data.comment,
            pr_approved=feedback_data.pr_approved,
            review_comments=feedback_data.review_comments,
            changes_requested=feedback_data.changes_requested,
            satisfaction_score=feedback_data.satisfaction_score,
            would_recommend=feedback_data.would_recommend,
            metadata=feedback_data.metadata
        )
        
        db.add(feedback_record)
        db.commit()
        
        # Process feedback through pipeline
        result = scoring_pipeline.process_feedback(feedback_data)
        
        logger.info(f"Feedback processed successfully for session {feedback_data.session_id}")
        return {
            "success": True,
            "feedback_id": feedback_data.feedback_id,
            "session_id": feedback_data.session_id,
            "processed": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Feedback endpoint error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/feedback/{session_id}", response_model=List[Dict[str, Any]], tags=["Feedback"])
async def get_session_feedback(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all feedback for a specific session
    
    Args:
        session_id: Session identifier
        db: Database session
    
    Returns:
        List of feedback records
    """
    try:
        feedback_records = db.query(FeedbackRecord).filter(
            FeedbackRecord.session_id == session_id
        ).all()
        
        feedback_list = []
        for record in feedback_records:
            feedback_list.append({
                "feedback_id": record.feedback_id,
                "scoring_id": record.scoring_id,
                "session_id": record.session_id,
                "feedback_type": record.feedback_type,
                "rating": record.rating,
                "comment": record.comment,
                "pr_approved": record.pr_approved,
                "review_comments": record.review_comments,
                "changes_requested": record.changes_requested,
                "satisfaction_score": record.satisfaction_score,
                "would_recommend": record.would_recommend,
                "created_at": record.created_at.isoformat(),
                "metadata": record.metadata
            })
        
        return feedback_list
        
    except Exception as e:
        logger.error(f"Get feedback endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# Analytics endpoints
@app.post("/api/v1/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
async def get_analytics(
    request: AnalyticsRequest,
    db: Session = Depends(get_db)
):
    """
    Get analytics data based on request parameters
    
    Args:
        request: Analytics request parameters
        db: Database session
    
    Returns:
        Analytics response with comprehensive data
    """
    try:
        logger.info("Analytics request received")
        
        # Build query based on request parameters
        query = db.query(ScoreRecord)
        
        # Apply filters
        if request.start_date:
            query = query.filter(ScoreRecord.created_at >= request.start_date)
        if request.end_date:
            query = query.filter(ScoreRecord.created_at <= request.end_date)
        if request.template_name:
            query = query.filter(ScoreRecord.template_name == request.template_name)
        if request.task_type:
            query = query.filter(ScoreRecord.task_type == request.task_type.value)
        
        # Execute query
        scores = query.limit(request.limit).offset(request.offset).all()
        
        # Calculate analytics
        total_scores = len(scores)
        average_score = sum(score.final_score for score in scores) / total_scores if total_scores > 0 else 0.0
        
        # Score distribution
        score_distribution = {}
        for score in scores:
            score_range = f"{int(score.final_score // 10) * 10}-{int(score.final_score // 10) * 10 + 9}"
            score_distribution[score_range] = score_distribution.get(score_range, 0) + 1
        
        # Template performance
        template_performance = []
        if request.include_dimensional:
            templates = db.query(TemplateRecord).all()
            for template in templates:
                template_performance.append(TemplatePerformance(
                    template_name=template.template_name,
                    template_version=template.template_version,
                    usage_count=template.usage_count,
                    average_score=template.average_score,
                    success_rate=template.success_rate,
                    avg_clarity=template.dimensional_averages.get('clarity', 0.0) if template.dimensional_averages else 0.0,
                    avg_coverage=template.dimensional_averages.get('coverage', 0.0) if template.dimensional_averages else 0.0,
                    avg_retry_penalty=template.dimensional_averages.get('retry_penalty', 0.0) if template.dimensional_averages else 0.0,
                    avg_edit_penalty=template.dimensional_averages.get('edit_penalty', 0.0) if template.dimensional_averages else 0.0,
                    avg_complexity_handling=template.dimensional_averages.get('complexity_handling', 0.0) if template.dimensional_averages else 0.0,
                    avg_performance_impact=template.dimensional_averages.get('performance_impact', 0.0) if template.dimensional_averages else 0.0,
                    avg_review_quality=template.dimensional_averages.get('review_quality', 0.0) if template.dimensional_averages else 0.0,
                    avg_developer_satisfaction=template.dimensional_averages.get('developer_satisfaction', 0.0) if template.dimensional_averages else 0.0,
                    last_updated=template.last_calculated
                ))
        
        # Create response
        analytics_response = AnalyticsResponse(
            total_scores=total_scores,
            average_score=average_score,
            score_distribution=score_distribution,
            template_performance=template_performance,
            recommendations=["Monitor template performance", "Optimize low-scoring templates"],
            alerts=["No critical alerts" if average_score > 70 else "Low average score detected"]
        )
        
        logger.info(f"Analytics completed: {total_scores} scores analyzed")
        return analytics_response
        
    except Exception as e:
        logger.error(f"Analytics endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/analytics/template/{template_name}", response_model=TemplatePerformance, tags=["Analytics"])
async def get_template_analytics(
    template_name: str,
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific template
    
    Args:
        template_name: Template name
        db: Database session
    
    Returns:
        Template performance data
    """
    try:
        template_record = db.query(TemplateRecord).filter(
            TemplateRecord.template_name == template_name
        ).first()
        
        if not template_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found"
            )
        
        template_performance = TemplatePerformance(
            template_name=template_record.template_name,
            template_version=template_record.template_version,
            usage_count=template_record.usage_count,
            average_score=template_record.average_score,
            success_rate=template_record.success_rate,
            avg_clarity=template_record.dimensional_averages.get('clarity', 0.0) if template_record.dimensional_averages else 0.0,
            avg_coverage=template_record.dimensional_averages.get('coverage', 0.0) if template_record.dimensional_averages else 0.0,
            avg_retry_penalty=template_record.dimensional_averages.get('retry_penalty', 0.0) if template_record.dimensional_averages else 0.0,
            avg_edit_penalty=template_record.dimensional_averages.get('edit_penalty', 0.0) if template_record.dimensional_averages else 0.0,
            avg_complexity_handling=template_record.dimensional_averages.get('complexity_handling', 0.0) if template_record.dimensional_averages else 0.0,
            avg_performance_impact=template_record.dimensional_averages.get('performance_impact', 0.0) if template_record.dimensional_averages else 0.0,
            avg_review_quality=template_record.dimensional_averages.get('review_quality', 0.0) if template_record.dimensional_averages else 0.0,
            avg_developer_satisfaction=template_record.dimensional_averages.get('developer_satisfaction', 0.0) if template_record.dimensional_averages else 0.0,
            last_updated=template_record.last_calculated,
            underperforming=template_record.underperforming,
            recommendations=template_record.recommendations or []
        )
        
        return template_performance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template analytics endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# System management endpoints
@app.get("/api/v1/system/health", response_model=Dict[str, Any], tags=["System"])
async def get_system_health():
    """
    Get comprehensive system health status
    
    Returns:
        System health information
    """
    try:
        health_status = scoring_pipeline.get_pipeline_health()
        
        # Add service-specific health checks
        health_status['service_info'] = {
            'name': 'PESS Scoring System',
            'version': '1.0.0',
            'uptime': datetime.utcnow().isoformat(),
            'database_connection': 'active'
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"System health endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/v1/system/metrics", response_model=Dict[str, Any], tags=["System"])
async def get_system_metrics():
    """
    Get comprehensive system metrics
    
    Returns:
        System performance metrics
    """
    try:
        metrics = scoring_pipeline.get_pipeline_metrics()
        
        # Add service-specific metrics
        metrics['service_metrics'] = {
            'requests_processed': metrics['pipeline_stats']['total_processed'],
            'success_rate': metrics['success_rate'],
            'avg_response_time': metrics['pipeline_stats']['avg_processing_time'],
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"System metrics endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/system/reset", response_model=Dict[str, Any], tags=["System"])
async def reset_system_stats():
    """
    Reset system statistics
    
    Returns:
        Reset confirmation
    """
    try:
        scoring_pipeline.reset_pipeline_stats()
        
        return {
            "success": True,
            "message": "System statistics reset successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System reset endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "pess_scoring.service:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    ) 