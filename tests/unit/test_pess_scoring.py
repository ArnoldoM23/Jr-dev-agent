"""
Unit tests for PESS (Prompt Effectiveness Scoring System) service.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../pess_scoring'))

from pess_scoring.models.scoring_models import (
    PromptData, ScoringRequest, ScoringResponse, 
    DimensionalScore, FeedbackData, AnalyticsData
)
from pess_scoring.core.scoring_algorithm import ScoringAlgorithm
from pess_scoring.core.ingestor import Ingestor
from pess_scoring.core.normalizer import Normalizer
from pess_scoring.core.evaluator import Evaluator
from pess_scoring.core.versioner import Versioner
from pess_scoring.core.emitter import Emitter
from pess_scoring.core.pipeline import PESSPipeline


class TestPESSModels:
    """Test PESS data models."""
    
    def test_prompt_data_creation(self):
        """Test PromptData model creation."""
        data = PromptData(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={"priority": "high"}
        )
        
        assert data.prompt == "Fix the login bug"
        assert data.context["ticket_id"] == "TICKET-123"
        assert data.metadata["priority"] == "high"
        assert data.timestamp is not None
    
    def test_scoring_request_validation(self):
        """Test ScoringRequest validation."""
        request = ScoringRequest(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={"priority": "high"}
        )
        
        assert request.prompt == "Fix the login bug"
        assert request.context["ticket_id"] == "TICKET-123"
        assert request.metadata["priority"] == "high"
    
    def test_dimensional_score_creation(self):
        """Test DimensionalScore model."""
        score = DimensionalScore(
            clarity=0.8,
            completeness=0.7,
            context_relevance=0.9,
            technical_accuracy=0.8,
            actionability=0.9,
            scope_appropriateness=0.8,
            error_handling=0.7,
            maintainability=0.8
        )
        
        assert score.clarity == 0.8
        assert score.completeness == 0.7
        assert score.context_relevance == 0.9
        assert score.technical_accuracy == 0.8
        assert score.actionability == 0.9
        assert score.scope_appropriateness == 0.8
        assert score.error_handling == 0.7
        assert score.maintainability == 0.8
    
    def test_scoring_response_creation(self):
        """Test ScoringResponse model creation."""
        dimensional_scores = DimensionalScore(
            clarity=0.8, completeness=0.7, context_relevance=0.9,
            technical_accuracy=0.8, actionability=0.9, scope_appropriateness=0.8,
            error_handling=0.7, maintainability=0.8
        )
        
        response = ScoringResponse(
            overall_score=0.8,
            dimensional_scores=dimensional_scores,
            recommendations=["Add more specific requirements"],
            confidence=0.85,
            metadata={"processing_time": 0.5}
        )
        
        assert response.overall_score == 0.8
        assert response.dimensional_scores.clarity == 0.8
        assert response.recommendations == ["Add more specific requirements"]
        assert response.confidence == 0.85
        assert response.metadata["processing_time"] == 0.5


class TestScoringAlgorithm:
    """Test the core scoring algorithm."""
    
    def test_scoring_algorithm_initialization(self):
        """Test ScoringAlgorithm initialization."""
        algorithm = ScoringAlgorithm()
        assert algorithm is not None
        assert hasattr(algorithm, 'calculate_dimensional_scores')
        assert hasattr(algorithm, 'calculate_overall_score')
    
    def test_clarity_scoring(self):
        """Test clarity dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        # Clear prompt
        clear_prompt = "Fix the login validation bug in the authentication system by adding email format validation"
        clarity_score = algorithm._calculate_clarity_score(clear_prompt)
        assert 0.0 <= clarity_score <= 1.0
        assert clarity_score > 0.5  # Should be reasonably high
        
        # Unclear prompt
        unclear_prompt = "fix it"
        unclear_score = algorithm._calculate_clarity_score(unclear_prompt)
        assert 0.0 <= unclear_score <= 1.0
        assert unclear_score < clarity_score  # Should be lower
    
    def test_completeness_scoring(self):
        """Test completeness dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        complete_prompt = "Fix the login validation bug by adding email format validation, password strength checking, and proper error messages"
        context = {"requirements": ["email validation", "password validation", "error handling"]}
        
        completeness_score = algorithm._calculate_completeness_score(complete_prompt, context)
        assert 0.0 <= completeness_score <= 1.0
        assert completeness_score > 0.5
    
    def test_context_relevance_scoring(self):
        """Test context relevance dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        prompt = "Fix the login validation bug"
        relevant_context = {"ticket_id": "AUTH-123", "component": "authentication", "priority": "high"}
        
        relevance_score = algorithm._calculate_context_relevance_score(prompt, relevant_context)
        assert 0.0 <= relevance_score <= 1.0
        assert relevance_score > 0.5
    
    def test_technical_accuracy_scoring(self):
        """Test technical accuracy dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        technical_prompt = "Fix the authentication bug by implementing proper JWT token validation with expiration checks"
        accuracy_score = algorithm._calculate_technical_accuracy_score(technical_prompt)
        assert 0.0 <= accuracy_score <= 1.0
        assert accuracy_score > 0.5
    
    def test_actionability_scoring(self):
        """Test actionability dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        actionable_prompt = "Add email format validation to the login form in src/auth.py"
        actionability_score = algorithm._calculate_actionability_score(actionable_prompt)
        assert 0.0 <= actionability_score <= 1.0
        assert actionability_score > 0.5
    
    def test_scope_appropriateness_scoring(self):
        """Test scope appropriateness dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        appropriate_prompt = "Fix the login validation bug"
        context = {"estimated_effort": "2 hours", "complexity": "medium"}
        
        scope_score = algorithm._calculate_scope_appropriateness_score(appropriate_prompt, context)
        assert 0.0 <= scope_score <= 1.0
        assert scope_score > 0.5
    
    def test_error_handling_scoring(self):
        """Test error handling dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        error_aware_prompt = "Fix the login bug and add proper error handling for invalid credentials"
        error_score = algorithm._calculate_error_handling_score(error_aware_prompt)
        assert 0.0 <= error_score <= 1.0
        assert error_score > 0.5
    
    def test_maintainability_scoring(self):
        """Test maintainability dimension scoring."""
        algorithm = ScoringAlgorithm()
        
        maintainable_prompt = "Fix the login bug with proper documentation and unit tests"
        maintainability_score = algorithm._calculate_maintainability_score(maintainable_prompt)
        assert 0.0 <= maintainability_score <= 1.0
        assert maintainability_score > 0.5
    
    def test_calculate_dimensional_scores(self):
        """Test complete dimensional scoring."""
        algorithm = ScoringAlgorithm()
        
        prompt_data = PromptData(
            prompt="Fix the login validation bug in the authentication system",
            context={"ticket_id": "AUTH-123", "priority": "high"},
            metadata={"estimated_effort": "2 hours"}
        )
        
        scores = algorithm.calculate_dimensional_scores(prompt_data)
        
        assert isinstance(scores, DimensionalScore)
        assert 0.0 <= scores.clarity <= 1.0
        assert 0.0 <= scores.completeness <= 1.0
        assert 0.0 <= scores.context_relevance <= 1.0
        assert 0.0 <= scores.technical_accuracy <= 1.0
        assert 0.0 <= scores.actionability <= 1.0
        assert 0.0 <= scores.scope_appropriateness <= 1.0
        assert 0.0 <= scores.error_handling <= 1.0
        assert 0.0 <= scores.maintainability <= 1.0
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        algorithm = ScoringAlgorithm()
        
        dimensional_scores = DimensionalScore(
            clarity=0.8, completeness=0.7, context_relevance=0.9,
            technical_accuracy=0.8, actionability=0.9, scope_appropriateness=0.8,
            error_handling=0.7, maintainability=0.8
        )
        
        overall_score = algorithm.calculate_overall_score(dimensional_scores)
        assert 0.0 <= overall_score <= 1.0
        assert abs(overall_score - 0.8) < 0.1  # Should be around the average


class TestIngestor:
    """Test the Ingestor component."""
    
    def test_ingestor_initialization(self):
        """Test Ingestor initialization."""
        ingestor = Ingestor()
        assert ingestor is not None
    
    @pytest.mark.asyncio
    async def test_ingest_scoring_request(self):
        """Test ingesting a scoring request."""
        ingestor = Ingestor()
        
        request = ScoringRequest(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={"priority": "high"}
        )
        
        result = await ingestor.ingest(request)
        
        assert isinstance(result, PromptData)
        assert result.prompt == "Fix the login bug"
        assert result.context["ticket_id"] == "TICKET-123"
        assert result.metadata["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_ingest_validation(self):
        """Test input validation during ingestion."""
        ingestor = Ingestor()
        
        # Test with invalid input
        with pytest.raises(ValueError):
            await ingestor.ingest(None)
        
        # Test with empty prompt
        with pytest.raises(ValueError):
            await ingestor.ingest(ScoringRequest(prompt="", context={}, metadata={}))


class TestNormalizer:
    """Test the Normalizer component."""
    
    def test_normalizer_initialization(self):
        """Test Normalizer initialization."""
        normalizer = Normalizer()
        assert normalizer is not None
    
    @pytest.mark.asyncio
    async def test_normalize_prompt_data(self):
        """Test normalizing prompt data."""
        normalizer = Normalizer()
        
        prompt_data = PromptData(
            prompt="  Fix the LOGIN bug  ",
            context={"ticket_id": "TICKET-123", "PRIORITY": "HIGH"},
            metadata={"estimated_effort": "2 HOURS"}
        )
        
        normalized = await normalizer.normalize(prompt_data)
        
        assert normalized.prompt == "Fix the LOGIN bug"  # Trimmed
        assert "PRIORITY" in normalized.context
        assert normalized.context["PRIORITY"] == "HIGH"
    
    @pytest.mark.asyncio
    async def test_normalize_context_enrichment(self):
        """Test context enrichment during normalization."""
        normalizer = Normalizer()
        
        prompt_data = PromptData(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={}
        )
        
        normalized = await normalizer.normalize(prompt_data)
        
        # Should have additional context
        assert "prompt_length" in normalized.context
        assert "word_count" in normalized.context
        assert normalized.context["prompt_length"] == len("Fix the login bug")


class TestEvaluator:
    """Test the Evaluator component."""
    
    def test_evaluator_initialization(self):
        """Test Evaluator initialization."""
        evaluator = Evaluator()
        assert evaluator is not None
        assert hasattr(evaluator, 'scoring_algorithm')
    
    @pytest.mark.asyncio
    async def test_evaluate_prompt_data(self):
        """Test evaluating prompt data."""
        evaluator = Evaluator()
        
        prompt_data = PromptData(
            prompt="Fix the login validation bug in the authentication system",
            context={"ticket_id": "AUTH-123", "priority": "high"},
            metadata={"estimated_effort": "2 hours"}
        )
        
        result = await evaluator.evaluate(prompt_data)
        
        assert hasattr(result, 'dimensional_scores')
        assert hasattr(result, 'overall_score')
        assert hasattr(result, 'recommendations')
        assert hasattr(result, 'confidence')
        
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self):
        """Test recommendation generation."""
        evaluator = Evaluator()
        
        # Low clarity score should generate clarity recommendations
        dimensional_scores = DimensionalScore(
            clarity=0.3, completeness=0.8, context_relevance=0.8,
            technical_accuracy=0.8, actionability=0.8, scope_appropriateness=0.8,
            error_handling=0.8, maintainability=0.8
        )
        
        recommendations = evaluator._generate_recommendations(dimensional_scores)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("clarity" in rec.lower() for rec in recommendations)


class TestVersioner:
    """Test the Versioner component."""
    
    def test_versioner_initialization(self):
        """Test Versioner initialization."""
        versioner = Versioner()
        assert versioner is not None
    
    @pytest.mark.asyncio
    async def test_version_scoring_result(self, mock_database):
        """Test versioning a scoring result."""
        versioner = Versioner()
        versioner.db = mock_database
        
        scoring_result = {
            "overall_score": 0.8,
            "dimensional_scores": {
                "clarity": 0.8,
                "completeness": 0.7,
                "context_relevance": 0.9,
                "technical_accuracy": 0.8,
                "actionability": 0.9,
                "scope_appropriateness": 0.8,
                "error_handling": 0.7,
                "maintainability": 0.8
            },
            "recommendations": ["Add more specific requirements"],
            "confidence": 0.85
        }
        
        versioned_result = await versioner.version(scoring_result)
        
        assert "version" in versioned_result
        assert "timestamp" in versioned_result
        assert versioned_result["overall_score"] == 0.8
        assert versioned_result["dimensional_scores"]["clarity"] == 0.8


class TestEmitter:
    """Test the Emitter component."""
    
    def test_emitter_initialization(self):
        """Test Emitter initialization."""
        emitter = Emitter()
        assert emitter is not None
    
    @pytest.mark.asyncio
    async def test_emit_scoring_response(self):
        """Test emitting a scoring response."""
        emitter = Emitter()
        
        versioned_result = {
            "overall_score": 0.8,
            "dimensional_scores": {
                "clarity": 0.8,
                "completeness": 0.7,
                "context_relevance": 0.9,
                "technical_accuracy": 0.8,
                "actionability": 0.9,
                "scope_appropriateness": 0.8,
                "error_handling": 0.7,
                "maintainability": 0.8
            },
            "recommendations": ["Add more specific requirements"],
            "confidence": 0.85,
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        response = await emitter.emit(versioned_result)
        
        assert isinstance(response, ScoringResponse)
        assert response.overall_score == 0.8
        assert response.dimensional_scores.clarity == 0.8
        assert response.recommendations == ["Add more specific requirements"]
        assert response.confidence == 0.85


class TestPESSPipeline:
    """Test the complete PESS pipeline."""
    
    def test_pipeline_initialization(self):
        """Test PESS pipeline initialization."""
        pipeline = PESSPipeline()
        assert pipeline is not None
        assert hasattr(pipeline, 'ingestor')
        assert hasattr(pipeline, 'normalizer')
        assert hasattr(pipeline, 'evaluator')
        assert hasattr(pipeline, 'versioner')
        assert hasattr(pipeline, 'emitter')
    
    @pytest.mark.asyncio
    async def test_pipeline_process_request(self):
        """Test complete pipeline processing."""
        pipeline = PESSPipeline()
        
        request = ScoringRequest(
            prompt="Fix the login validation bug in the authentication system",
            context={"ticket_id": "AUTH-123", "priority": "high"},
            metadata={"estimated_effort": "2 hours"}
        )
        
        # Mock the database for versioner
        with patch.object(pipeline.versioner, 'db', MagicMock()):
            response = await pipeline.process(request)
        
        assert isinstance(response, ScoringResponse)
        assert 0.0 <= response.overall_score <= 1.0
        assert 0.0 <= response.confidence <= 1.0
        assert isinstance(response.recommendations, list)
        assert hasattr(response, 'dimensional_scores')
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        pipeline = PESSPipeline()
        
        # Test with invalid request
        with pytest.raises(ValueError):
            await pipeline.process(None)
    
    @pytest.mark.asyncio
    async def test_pipeline_stages(self):
        """Test individual pipeline stages."""
        pipeline = PESSPipeline()
        
        request = ScoringRequest(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={"priority": "high"}
        )
        
        # Test ingestion stage
        prompt_data = await pipeline.ingestor.ingest(request)
        assert isinstance(prompt_data, PromptData)
        
        # Test normalization stage
        normalized_data = await pipeline.normalizer.normalize(prompt_data)
        assert isinstance(normalized_data, PromptData)
        
        # Test evaluation stage
        evaluation_result = await pipeline.evaluator.evaluate(normalized_data)
        assert hasattr(evaluation_result, 'overall_score')
        
        # Test versioning stage
        with patch.object(pipeline.versioner, 'db', MagicMock()):
            versioned_result = await pipeline.versioner.version(evaluation_result.__dict__)
            assert "version" in versioned_result
        
        # Test emission stage
        final_response = await pipeline.emitter.emit(versioned_result)
        assert isinstance(final_response, ScoringResponse)


class TestPESSIntegration:
    """Test PESS service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_high_quality_prompt_scoring(self):
        """Test scoring of a high-quality prompt."""
        pipeline = PESSPipeline()
        
        high_quality_request = ScoringRequest(
            prompt="Fix the login validation bug by implementing proper email format validation using regex patterns, adding password strength requirements with minimum 8 characters including uppercase, lowercase, and numbers, and implementing proper error handling with user-friendly messages",
            context={
                "ticket_id": "AUTH-123",
                "priority": "high",
                "component": "authentication",
                "estimated_effort": "4 hours",
                "requirements": ["email validation", "password validation", "error handling"]
            },
            metadata={
                "developer_level": "senior",
                "codebase_size": "large",
                "complexity": "medium"
            }
        )
        
        with patch.object(pipeline.versioner, 'db', MagicMock()):
            response = await pipeline.process(high_quality_request)
        
        assert response.overall_score >= 0.7  # Should be high quality
        assert response.confidence >= 0.7
        assert len(response.recommendations) <= 2  # Should need few recommendations
    
    @pytest.mark.asyncio
    async def test_low_quality_prompt_scoring(self):
        """Test scoring of a low-quality prompt."""
        pipeline = PESSPipeline()
        
        low_quality_request = ScoringRequest(
            prompt="fix it",
            context={},
            metadata={}
        )
        
        with patch.object(pipeline.versioner, 'db', MagicMock()):
            response = await pipeline.process(low_quality_request)
        
        assert response.overall_score <= 0.5  # Should be low quality
        assert len(response.recommendations) >= 3  # Should need many recommendations
    
    @pytest.mark.asyncio
    async def test_retry_penalty_application(self):
        """Test retry penalty application."""
        pipeline = PESSPipeline()
        
        request = ScoringRequest(
            prompt="Fix the login bug",
            context={"ticket_id": "TICKET-123"},
            metadata={"retry_count": 3}  # Multiple retries
        )
        
        with patch.object(pipeline.versioner, 'db', MagicMock()):
            response = await pipeline.process(request)
        
        # Score should be penalized for retries
        assert response.overall_score < 0.8  # Should be penalized
        assert "retry" in " ".join(response.recommendations).lower() 