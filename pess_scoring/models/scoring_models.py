"""
PESS Scoring Models

Pydantic models for the Prompt Effectiveness Scoring System including:
- Input/output models for scoring pipeline
- 8-dimensional scoring metrics
- Feedback integration models
- Analytics and trending models
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

class TaskType(str, Enum):
    """Supported task types for scoring"""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    VERSION_UPGRADE = "version_upgrade"
    CONFIG_UPDATE = "config_update"
    SCHEMA_CHANGE = "schema_change"
    RESOLVER_ADDITION = "resolver_addition"
    DEPLOYMENT_PIPELINE = "deployment_pipeline"
    TEST_GENERATION = "test_generation"

class ScoringStage(str, Enum):
    """5-stage pipeline stages"""
    INGESTOR = "ingestor"
    NORMALIZER = "normalizer"
    EVALUATOR = "evaluator"
    VERSIONER = "versioner"
    EMITTER = "emitter"

class FeedbackType(str, Enum):
    """Types of feedback for scoring"""
    DEVELOPER_SATISFACTION = "developer_satisfaction"
    PR_REVIEW = "pr_review"
    RETRY_FEEDBACK = "retry_feedback"
    MANUAL_EDIT = "manual_edit"

class ScoringInput(BaseModel):
    """Input data for the scoring pipeline"""
    session_id: str = Field(..., description="Unique session identifier")
    ticket_id: str = Field(..., description="Jira ticket identifier")
    task_type: TaskType = Field(..., description="Type of task being scored")
    template_name: str = Field(..., description="Template used for prompt generation")
    template_version: str = Field(..., description="Version of template used")
    prompt_hash: str = Field(..., description="SHA256 hash of generated prompt")
    
    # Metrics for scoring
    retry_count: int = Field(0, ge=0, description="Number of retry attempts")
    edit_similarity: float = Field(1.0, ge=0.0, le=1.0, description="Similarity between original and edited code")
    complexity_score: float = Field(0.5, ge=0.0, le=1.0, description="Task complexity score")
    perf_before: float = Field(0.0, ge=0.0, description="Performance metric before changes")
    perf_after: float = Field(0.0, ge=0.0, description="Performance metric after changes")
    
    # File and context information
    files_referenced: List[str] = Field(default_factory=list, description="Files referenced in prompt")
    test_coverage: float = Field(0.0, ge=0.0, le=1.0, description="Test coverage percentage")
    
    # Timing information
    generation_time: float = Field(0.0, ge=0.0, description="Time taken to generate prompt (seconds)")
    execution_time: float = Field(0.0, ge=0.0, description="Time taken to execute task (seconds)")
    
    # Optional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('prompt_hash')
    def validate_prompt_hash(cls, v):
        if len(v) != 64:  # SHA256 hash length
            raise ValueError("prompt_hash must be a valid SHA256 hash")
        return v

class DimensionalScores(BaseModel):
    """8-dimensional scoring metrics"""
    clarity: float = Field(..., ge=0.0, le=1.0, description="Template structure and instruction completeness")
    coverage: float = Field(..., ge=0.0, le=1.0, description="File references and test case inclusion")
    retry_penalty: float = Field(..., ge=0.0, le=1.0, description="Penalty based on retry attempts")
    edit_penalty: float = Field(..., ge=0.0, le=1.0, description="Penalty for manual developer edits")
    complexity_handling: float = Field(..., ge=0.0, le=1.0, description="Adjustment based on task complexity")
    performance_impact: float = Field(..., ge=0.0, le=1.0, description="Before/after operation metrics")
    review_quality: float = Field(..., ge=0.0, le=1.0, description="PR review feedback and approval rates")
    developer_satisfaction: float = Field(..., ge=0.0, le=1.0, description="Manual feedback and ratings")

class ScoringMetrics(BaseModel):
    """Comprehensive scoring metrics"""
    base_score: float = Field(..., ge=0.0, le=100.0, description="Base score before adjustments")
    final_score: float = Field(..., ge=0.0, le=100.0, description="Final adjusted score")
    dimensional_scores: DimensionalScores = Field(..., description="Detailed dimensional scores")
    
    # Calculation details
    adjustments: Dict[str, float] = Field(default_factory=dict, description="Applied adjustments")
    penalties: Dict[str, float] = Field(default_factory=dict, description="Applied penalties")
    bonuses: Dict[str, float] = Field(default_factory=dict, description="Applied bonuses")

class ScoringOutput(BaseModel):
    """Output from the scoring pipeline"""
    scoring_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique scoring ID")
    session_id: str = Field(..., description="Associated session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Scoring timestamp")
    
    # Scoring results
    metrics: ScoringMetrics = Field(..., description="Comprehensive scoring metrics")
    
    # Pipeline metadata
    pipeline_stage: ScoringStage = Field(..., description="Current pipeline stage")
    processing_time: float = Field(0.0, ge=0.0, description="Time taken to process scoring")
    
    # Versioning information
    template_correlation: Dict[str, str] = Field(default_factory=dict, description="Template and hash correlation")
    score_version: str = Field("1.0", description="Scoring algorithm version")
    
    # Quality indicators
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in scoring accuracy")
    data_quality: float = Field(1.0, ge=0.0, le=1.0, description="Quality of input data")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    alerts: List[str] = Field(default_factory=list, description="Performance alerts")

class FeedbackData(BaseModel):
    """Feedback data for scoring improvement"""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique feedback ID")
    scoring_id: str = Field(..., description="Associated scoring ID")
    session_id: str = Field(..., description="Associated session ID")
    
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Feedback timestamp")
    
    # Feedback content
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Numeric rating (0-5)")
    comment: Optional[str] = Field(None, description="Textual feedback")
    
    # PR review specific
    pr_approved: Optional[bool] = Field(None, description="Whether PR was approved")
    review_comments: Optional[int] = Field(None, ge=0, description="Number of review comments")
    changes_requested: Optional[bool] = Field(None, description="Whether changes were requested")
    
    # Developer satisfaction specific
    satisfaction_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Developer satisfaction score")
    would_recommend: Optional[bool] = Field(None, description="Would recommend this approach")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional feedback metadata")

class ScoreHistory(BaseModel):
    """Historical scoring data"""
    session_id: str = Field(..., description="Session identifier")
    scores: List[ScoringOutput] = Field(..., description="Historical scores")
    feedback: List[FeedbackData] = Field(default_factory=list, description="Associated feedback")
    
    # Trend analysis
    trend_direction: str = Field("stable", description="Score trend direction")
    improvement_rate: float = Field(0.0, description="Rate of improvement")
    
    # Statistics
    average_score: float = Field(0.0, ge=0.0, le=100.0, description="Average score")
    score_variance: float = Field(0.0, ge=0.0, description="Score variance")
    best_score: float = Field(0.0, ge=0.0, le=100.0, description="Best score achieved")
    worst_score: float = Field(0.0, ge=0.0, le=100.0, description="Worst score achieved")

class TemplatePerformance(BaseModel):
    """Template performance analytics"""
    template_name: str = Field(..., description="Template identifier")
    template_version: str = Field(..., description="Template version")
    
    # Performance metrics
    usage_count: int = Field(0, ge=0, description="Number of times used")
    average_score: float = Field(0.0, ge=0.0, le=100.0, description="Average score")
    success_rate: float = Field(0.0, ge=0.0, le=1.0, description="Success rate")
    
    # Dimensional averages
    avg_clarity: float = Field(0.0, ge=0.0, le=1.0, description="Average clarity score")
    avg_coverage: float = Field(0.0, ge=0.0, le=1.0, description="Average coverage score")
    avg_retry_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Average retry penalty")
    avg_edit_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Average edit penalty")
    avg_complexity_handling: float = Field(0.0, ge=0.0, le=1.0, description="Average complexity handling")
    avg_performance_impact: float = Field(0.0, ge=0.0, le=1.0, description="Average performance impact")
    avg_review_quality: float = Field(0.0, ge=0.0, le=1.0, description="Average review quality")
    avg_developer_satisfaction: float = Field(0.0, ge=0.0, le=1.0, description="Average developer satisfaction")
    
    # Trend data
    trend_data: List[float] = Field(default_factory=list, description="Score trend over time")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Alerts and recommendations
    underperforming: bool = Field(False, description="Whether template is underperforming")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

class AnalyticsRequest(BaseModel):
    """Request for analytics data"""
    start_date: Optional[datetime] = Field(None, description="Start date for analytics")
    end_date: Optional[datetime] = Field(None, description="End date for analytics")
    template_name: Optional[str] = Field(None, description="Filter by template name")
    task_type: Optional[TaskType] = Field(None, description="Filter by task type")
    
    # Aggregation options
    group_by: Optional[str] = Field(None, description="Group results by field")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    
    # Metrics to include
    include_trends: bool = Field(True, description="Include trend analysis")
    include_dimensional: bool = Field(True, description="Include dimensional breakdowns")
    include_feedback: bool = Field(True, description="Include feedback correlation")

class AnalyticsResponse(BaseModel):
    """Response with analytics data"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    # Summary statistics
    total_scores: int = Field(0, ge=0, description="Total number of scores")
    average_score: float = Field(0.0, ge=0.0, le=100.0, description="Overall average score")
    score_distribution: Dict[str, int] = Field(default_factory=dict, description="Score distribution")
    
    # Template performance
    template_performance: List[TemplatePerformance] = Field(default_factory=list, description="Template performance data")
    
    # Trend analysis
    trend_analysis: Dict[str, Any] = Field(default_factory=dict, description="Trend analysis results")
    
    # Dimensional analysis
    dimensional_analysis: Dict[str, float] = Field(default_factory=dict, description="Dimensional score analysis")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="System recommendations")
    alerts: List[str] = Field(default_factory=list, description="Performance alerts")
    
    # Metadata
    processing_time: float = Field(0.0, ge=0.0, description="Time taken to process request")
    data_freshness: datetime = Field(default_factory=datetime.utcnow, description="Data freshness timestamp") 