"""
PESS Database Models

SQLAlchemy models for PostgreSQL database integration with JSONB support
for dimensional scores and 2-year data retention.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timedelta

Base = declarative_base()

class ScoreRecord(Base):
    """Main scoring record with JSONB dimensional scores"""
    __tablename__ = "score_records"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scoring_id = Column(String(50), unique=True, nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    
    # Ticket and task information
    ticket_id = Column(String(50), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    template_name = Column(String(100), nullable=False, index=True)
    template_version = Column(String(20), nullable=False)
    prompt_hash = Column(String(64), nullable=False)
    
    # Scoring results (JSONB for flexible dimensional scores)
    base_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False, index=True)
    dimensional_scores = Column(JSONB, nullable=False)
    adjustments = Column(JSONB)
    penalties = Column(JSONB)
    bonuses = Column(JSONB)
    
    # Pipeline metadata
    pipeline_stage = Column(String(20), nullable=False)
    processing_time = Column(Float, default=0.0)
    score_version = Column(String(10), default="1.0")
    
    # Quality indicators
    confidence_score = Column(Float, default=1.0)
    data_quality = Column(Float, default=1.0)
    
    # Metrics for scoring
    retry_count = Column(Integer, default=0)
    edit_similarity = Column(Float, default=1.0)
    complexity_score = Column(Float, default=0.5)
    perf_before = Column(Float, default=0.0)
    perf_after = Column(Float, default=0.0)
    test_coverage = Column(Float, default=0.0)
    generation_time = Column(Float, default=0.0)
    execution_time = Column(Float, default=0.0)
    
    # File and context information (JSONB for flexible structure)
    files_referenced = Column(JSONB)
    template_correlation = Column(JSONB)
    recommendations = Column(JSONB)
    alerts = Column(JSONB)
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feedback_records = relationship("FeedbackRecord", back_populates="score_record")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_score_session_date', 'session_id', 'created_at'),
        Index('idx_score_template_date', 'template_name', 'created_at'),
        Index('idx_score_task_type_date', 'task_type', 'created_at'),
        Index('idx_score_final_score_date', 'final_score', 'created_at'),
        Index('idx_score_dimensional_gin', 'dimensional_scores', postgresql_using='gin'),
    )

class FeedbackRecord(Base):
    """Feedback record for developer satisfaction and PR reviews"""
    __tablename__ = "feedback_records"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(String(50), unique=True, nullable=False, index=True)
    scoring_id = Column(String(50), ForeignKey('score_records.scoring_id'), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    
    # Feedback type and content
    feedback_type = Column(String(50), nullable=False, index=True)
    rating = Column(Float)
    comment = Column(Text)
    
    # PR review specific fields
    pr_approved = Column(Boolean)
    review_comments = Column(Integer)
    changes_requested = Column(Boolean)
    
    # Developer satisfaction specific fields
    satisfaction_score = Column(Float)
    would_recommend = Column(Boolean)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    score_record = relationship("ScoreRecord", back_populates="feedback_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_type_date', 'feedback_type', 'created_at'),
        Index('idx_feedback_scoring_date', 'scoring_id', 'created_at'),
    )

class TemplateRecord(Base):
    """Template performance tracking"""
    __tablename__ = "template_records"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(100), nullable=False, index=True)
    template_version = Column(String(20), nullable=False)
    
    # Performance metrics
    usage_count = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    
    # Dimensional averages (JSONB for flexible structure)
    dimensional_averages = Column(JSONB)
    
    # Trend data
    trend_data = Column(JSONB)
    
    # Alerts and recommendations
    underperforming = Column(Boolean, default=False)
    recommendations = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_calculated = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint on template name and version
    __table_args__ = (
        Index('idx_template_name_version', 'template_name', 'template_version', unique=True),
        Index('idx_template_performance', 'average_score', 'success_rate'),
    )

class SessionRecord(Base):
    """Session tracking for scoring lifecycle"""
    __tablename__ = "session_records"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Session information
    ticket_id = Column(String(50), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    template_name = Column(String(100), nullable=False)
    template_version = Column(String(20), nullable=False)
    
    # Session status
    status = Column(String(20), default="active", index=True)  # active, completed, failed
    
    # Scoring summary
    total_scores = Column(Integer, default=0)
    best_score = Column(Float, default=0.0)
    worst_score = Column(Float, default=0.0)
    average_score = Column(Float, default=0.0)
    
    # Trend analysis
    trend_direction = Column(String(20), default="stable")
    improvement_rate = Column(Float, default=0.0)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_session_ticket_date', 'ticket_id', 'created_at'),
        Index('idx_session_status_date', 'status', 'created_at'),
    )

class DataRetentionPolicy(Base):
    """Data retention policy for 2-year retention requirement"""
    __tablename__ = "data_retention_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(String(50), nullable=False, unique=True)
    retention_days = Column(Integer, nullable=False, default=730)  # 2 years
    last_cleanup = Column(DateTime, default=datetime.utcnow)
    next_cleanup = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    # Cleanup statistics
    records_cleaned = Column(Integer, default=0)
    cleanup_duration = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database utility functions for common queries
def get_recent_scores(session, days=30, limit=100):
    """Get recent scores for analytics"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return session.query(ScoreRecord).filter(
        ScoreRecord.created_at >= cutoff
    ).order_by(ScoreRecord.created_at.desc()).limit(limit).all()

def get_template_performance(session, template_name=None, days=30):
    """Get template performance metrics"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = session.query(ScoreRecord).filter(
        ScoreRecord.created_at >= cutoff
    )
    if template_name:
        query = query.filter(ScoreRecord.template_name == template_name)
    return query.all()

def get_dimensional_averages(session, template_name=None, days=30):
    """Get dimensional score averages"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = session.query(
        func.avg(ScoreRecord.final_score).label('avg_final_score'),
        func.avg(ScoreRecord.retry_count).label('avg_retry_count'),
        func.avg(ScoreRecord.edit_similarity).label('avg_edit_similarity'),
        func.avg(ScoreRecord.complexity_score).label('avg_complexity_score'),
        func.avg(ScoreRecord.test_coverage).label('avg_test_coverage')
    ).filter(ScoreRecord.created_at >= cutoff)
    
    if template_name:
        query = query.filter(ScoreRecord.template_name == template_name)
    
    return query.first()

def cleanup_old_records(session, retention_days=730):
    """Clean up old records based on retention policy"""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    
    # Clean up old score records
    deleted_scores = session.query(ScoreRecord).filter(
        ScoreRecord.created_at < cutoff
    ).delete()
    
    # Clean up old feedback records
    deleted_feedback = session.query(FeedbackRecord).filter(
        FeedbackRecord.created_at < cutoff
    ).delete()
    
    # Clean up old session records
    deleted_sessions = session.query(SessionRecord).filter(
        SessionRecord.created_at < cutoff
    ).delete()
    
    session.commit()
    
    return {
        'deleted_scores': deleted_scores,
        'deleted_feedback': deleted_feedback,
        'deleted_sessions': deleted_sessions,
        'total_deleted': deleted_scores + deleted_feedback + deleted_sessions
    } 