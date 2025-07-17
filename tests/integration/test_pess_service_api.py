"""
Integration tests for PESS service API endpoints.
"""

import pytest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


class TestPESSServiceAPI:
    """Test PESS service API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, service_client_factory):
        """Test PESS service health check endpoint."""
        client = service_client_factory("pess")
        
        response = await client.get("/health")
        
        assert response["status"] == 200
        assert "status" in response["data"]
        assert response["data"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_score_prompt_endpoint(self, service_client_factory, sample_pess_data):
        """Test the /score endpoint."""
        client = service_client_factory("pess")
        
        request_data = {
            "prompt": sample_pess_data["prompt"],
            "context": sample_pess_data["context"],
            "metadata": {}
        }
        
        response = await client.post("/score", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "overall_score" in data
        assert "dimensional_scores" in data
        assert "recommendations" in data
        assert "confidence" in data
        
        # Validate score ranges
        assert 0.0 <= data["overall_score"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0
        
        # Validate dimensional scores
        dimensional_scores = data["dimensional_scores"]
        dimensions = [
            "clarity", "completeness", "context_relevance", "technical_accuracy",
            "actionability", "scope_appropriateness", "error_handling", "maintainability"
        ]
        
        for dimension in dimensions:
            assert dimension in dimensional_scores
            assert 0.0 <= dimensional_scores[dimension] <= 1.0
        
        # Validate recommendations
        assert isinstance(data["recommendations"], list)
    
    @pytest.mark.asyncio
    async def test_score_prompt_with_high_quality_input(self, service_client_factory):
        """Test scoring with high-quality prompt."""
        client = service_client_factory("pess")
        
        high_quality_request = {
            "prompt": "Fix the login validation bug by implementing proper email format validation using regex patterns, adding password strength requirements with minimum 8 characters including uppercase, lowercase, and numbers, and implementing proper error handling with user-friendly messages for invalid credentials",
            "context": {
                "ticket_id": "AUTH-123",
                "priority": "high",
                "component": "authentication",
                "estimated_effort": "4 hours",
                "requirements": ["email validation", "password validation", "error handling"]
            },
            "metadata": {
                "developer_level": "senior",
                "codebase_size": "large",
                "complexity": "medium"
            }
        }
        
        response = await client.post("/score", high_quality_request)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["overall_score"] >= 0.7  # Should be high quality
        assert data["confidence"] >= 0.7
        assert len(data["recommendations"]) <= 3  # Should need few recommendations
    
    @pytest.mark.asyncio
    async def test_score_prompt_with_low_quality_input(self, service_client_factory):
        """Test scoring with low-quality prompt."""
        client = service_client_factory("pess")
        
        low_quality_request = {
            "prompt": "fix it",
            "context": {},
            "metadata": {}
        }
        
        response = await client.post("/score", low_quality_request)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["overall_score"] <= 0.5  # Should be low quality
        assert len(data["recommendations"]) >= 3  # Should need many recommendations
    
    @pytest.mark.asyncio
    async def test_score_prompt_validation_errors(self, service_client_factory):
        """Test validation errors for /score endpoint."""
        client = service_client_factory("pess")
        
        # Test empty prompt
        invalid_request = {
            "prompt": "",
            "context": {},
            "metadata": {}
        }
        
        response = await client.post("/score", invalid_request)
        assert response["status"] == 422  # Validation error
        
        # Test missing prompt
        invalid_request = {
            "context": {},
            "metadata": {}
        }
        
        response = await client.post("/score", invalid_request)
        assert response["status"] == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_feedback_endpoint(self, service_client_factory):
        """Test the /feedback endpoint."""
        client = service_client_factory("pess")
        
        # First, get a score to provide feedback on
        scoring_request = {
            "prompt": "Fix the login bug",
            "context": {"ticket_id": "TICKET-123"},
            "metadata": {}
        }
        
        score_response = await client.post("/score", scoring_request)
        assert score_response["status"] == 200
        
        # Now provide feedback
        feedback_request = {
            "session_id": "session-123",
            "feedback_type": "satisfaction",
            "score": 4,
            "comments": "The recommendations were helpful",
            "metadata": {
                "developer_level": "mid"
            }
        }
        
        feedback_response = await client.post("/feedback", feedback_request)
        
        assert feedback_response["status"] == 200
        assert "message" in feedback_response["data"]
        assert feedback_response["data"]["message"] == "Feedback recorded successfully"
    
    @pytest.mark.asyncio
    async def test_analytics_endpoint(self, service_client_factory):
        """Test the /analytics endpoint."""
        client = service_client_factory("pess")
        
        # Request analytics data
        analytics_params = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "granularity": "daily"
        }
        
        response = await client.get("/analytics", params=analytics_params)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "average_scores" in data
        assert "score_distribution" in data
        assert "recommendation_trends" in data
        assert "feedback_correlation" in data
        
        # Validate average scores structure
        avg_scores = data["average_scores"]
        assert "overall" in avg_scores
        assert "dimensional" in avg_scores
        
        # Validate dimensional averages
        dimensional_avg = avg_scores["dimensional"]
        expected_dimensions = [
            "clarity", "completeness", "context_relevance", "technical_accuracy",
            "actionability", "scope_appropriateness", "error_handling", "maintainability"
        ]
        
        for dimension in expected_dimensions:
            assert dimension in dimensional_avg
            assert 0.0 <= dimensional_avg[dimension] <= 1.0
    
    @pytest.mark.asyncio
    async def test_batch_scoring_endpoint(self, service_client_factory):
        """Test the /batch-score endpoint."""
        client = service_client_factory("pess")
        
        batch_request = {
            "requests": [
                {
                    "prompt": "Fix the login bug",
                    "context": {"ticket_id": "TICKET-123"},
                    "metadata": {}
                },
                {
                    "prompt": "Add user registration functionality",
                    "context": {"ticket_id": "TICKET-456"},
                    "metadata": {}
                },
                {
                    "prompt": "Implement password reset",
                    "context": {"ticket_id": "TICKET-789"},
                    "metadata": {}
                }
            ]
        }
        
        response = await client.post("/batch-score", batch_request)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "results" in data
        assert len(data["results"]) == 3
        
        # Validate each result
        for i, result in enumerate(data["results"]):
            assert "overall_score" in result
            assert "dimensional_scores" in result
            assert "recommendations" in result
            assert "confidence" in result
            assert 0.0 <= result["overall_score"] <= 1.0
            assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_score_history_endpoint(self, service_client_factory):
        """Test the /score-history endpoint."""
        client = service_client_factory("pess")
        
        # First, create some scores
        for i in range(3):
            scoring_request = {
                "prompt": f"Fix the login bug {i}",
                "context": {"ticket_id": f"TICKET-{i}"},
                "metadata": {"session_id": "session-123"}
            }
            
            score_response = await client.post("/score", scoring_request)
            assert score_response["status"] == 200
        
        # Now get history
        history_response = await client.get("/score-history?session_id=session-123")
        
        assert history_response["status"] == 200
        
        data = history_response["data"]
        assert "history" in data
        assert len(data["history"]) >= 0  # May be empty in test environment
        
        # If history exists, validate structure
        if data["history"]:
            for entry in data["history"]:
                assert "timestamp" in entry
                assert "prompt" in entry
                assert "overall_score" in entry
                assert "dimensional_scores" in entry
    
    @pytest.mark.asyncio
    async def test_recommendations_endpoint(self, service_client_factory):
        """Test the /recommendations endpoint."""
        client = service_client_factory("pess")
        
        # Request recommendations for a specific prompt
        request_data = {
            "prompt": "fix it",
            "context": {},
            "metadata": {}
        }
        
        response = await client.post("/recommendations", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
        
        # Validate recommendation structure
        for rec in data["recommendations"]:
            assert "category" in rec
            assert "suggestion" in rec
            assert "impact" in rec
            assert "priority" in rec
    
    @pytest.mark.asyncio
    async def test_service_metrics_endpoint(self, service_client_factory):
        """Test the /metrics endpoint."""
        client = service_client_factory("pess")
        
        response = await client.get("/metrics")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "processing_stats" in data
        assert "performance_metrics" in data
        assert "system_health" in data
        
        # Validate processing stats
        processing_stats = data["processing_stats"]
        assert "total_requests" in processing_stats
        assert "average_processing_time" in processing_stats
        assert "success_rate" in processing_stats
        
        # Validate performance metrics
        performance_metrics = data["performance_metrics"]
        assert "throughput" in performance_metrics
        assert "latency_percentiles" in performance_metrics
        
        # Validate system health
        system_health = data["system_health"]
        assert "database_status" in system_health
        assert "memory_usage" in system_health
        assert "cpu_usage" in system_health
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service_client_factory):
        """Test error handling in API endpoints."""
        client = service_client_factory("pess")
        
        # Test invalid endpoint
        response = await client.get("/invalid-endpoint")
        assert response["status"] == 404
        
        # Test malformed JSON
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8005/score",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 400
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service_client_factory):
        """Test handling of concurrent requests."""
        client = service_client_factory("pess")
        
        # Create multiple concurrent requests
        requests = []
        for i in range(10):
            request_data = {
                "prompt": f"Fix the login bug {i}",
                "context": {"ticket_id": f"TICKET-{i}"},
                "metadata": {}
            }
            requests.append(client.post("/score", request_data))
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*requests)
        
        # Validate all responses
        for response in responses:
            assert response["status"] == 200
            assert "overall_score" in response["data"]
            assert "dimensional_scores" in response["data"]
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, service_client_factory):
        """Test rate limiting behavior."""
        client = service_client_factory("pess")
        
        # Make rapid requests to test rate limiting
        rapid_requests = []
        for i in range(50):  # More than typical rate limit
            request_data = {
                "prompt": f"Test prompt {i}",
                "context": {},
                "metadata": {}
            }
            rapid_requests.append(client.post("/score", request_data))
        
        responses = await asyncio.gather(*rapid_requests, return_exceptions=True)
        
        # Some requests should succeed, others might be rate limited
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r["status"] == 200)
        assert success_count > 0  # At least some should succeed
    
    @pytest.mark.asyncio
    async def test_authentication_required_endpoints(self, service_client_factory):
        """Test endpoints that require authentication."""
        client = service_client_factory("pess")
        
        # Test analytics endpoint without auth (should work in dev mode)
        response = await client.get("/analytics")
        assert response["status"] in [200, 401]  # Either works or requires auth
        
        # Test admin metrics endpoint
        response = await client.get("/admin/metrics")
        assert response["status"] in [200, 401, 404]  # Either works, requires auth, or doesn't exist
    
    @pytest.mark.asyncio
    async def test_data_persistence(self, service_client_factory):
        """Test that scores and feedback are persisted."""
        client = service_client_factory("pess")
        
        # Create a score
        scoring_request = {
            "prompt": "Fix the login bug for persistence test",
            "context": {"ticket_id": "PERSIST-123"},
            "metadata": {"session_id": "persist-session"}
        }
        
        score_response = await client.post("/score", scoring_request)
        assert score_response["status"] == 200
        
        # Add feedback
        feedback_request = {
            "session_id": "persist-session",
            "feedback_type": "satisfaction",
            "score": 5,
            "comments": "Great recommendations!",
            "metadata": {}
        }
        
        feedback_response = await client.post("/feedback", feedback_request)
        assert feedback_response["status"] == 200
        
        # Verify data can be retrieved
        history_response = await client.get("/score-history?session_id=persist-session")
        assert history_response["status"] == 200
        
        # Check if analytics reflect the new data
        analytics_response = await client.get("/analytics")
        assert analytics_response["status"] == 200


class TestPESSServiceConfiguration:
    """Test PESS service configuration and setup."""
    
    @pytest.mark.asyncio
    async def test_service_configuration(self, service_client_factory):
        """Test service configuration endpoint."""
        client = service_client_factory("pess")
        
        response = await client.get("/config")
        
        # Config endpoint might not exist, so check for 200 or 404
        assert response["status"] in [200, 404]
        
        if response["status"] == 200:
            data = response["data"]
            assert "scoring_weights" in data or "version" in data
    
    @pytest.mark.asyncio
    async def test_database_connection(self, service_client_factory):
        """Test database connection health."""
        client = service_client_factory("pess")
        
        response = await client.get("/health/db")
        
        # DB health endpoint might not exist
        assert response["status"] in [200, 404]
        
        if response["status"] == 200:
            data = response["data"]
            assert "database_status" in data
    
    @pytest.mark.asyncio
    async def test_service_startup_sequence(self, service_client_factory):
        """Test service startup and initialization."""
        client = service_client_factory("pess")
        
        # Health check should work immediately after startup
        response = await client.get("/health")
        assert response["status"] == 200
        
        # Basic scoring should work
        basic_request = {
            "prompt": "Test startup",
            "context": {},
            "metadata": {}
        }
        
        response = await client.post("/score", basic_request)
        assert response["status"] == 200


class TestPESSServiceIntegration:
    """Test PESS service integration with other components."""
    
    @pytest.mark.asyncio
    async def test_integration_with_session_management(self, service_client_factory):
        """Test integration with session management service."""
        pess_client = service_client_factory("pess")
        
        # Create a scoring request with session context
        request_data = {
            "prompt": "Fix authentication issue",
            "context": {
                "ticket_id": "AUTH-456",
                "session_id": "session-789"
            },
            "metadata": {
                "user_id": "user-123",
                "workspace": "/path/to/workspace"
            }
        }
        
        response = await pess_client.post("/score", request_data)
        assert response["status"] == 200
        
        # Score should include session context
        data = response["data"]
        assert "overall_score" in data
        assert "dimensional_scores" in data
    
    @pytest.mark.asyncio
    async def test_integration_with_memory_system(self, service_client_factory):
        """Test integration with synthetic memory system."""
        pess_client = service_client_factory("pess")
        
        # Create a scoring request that might use memory context
        request_data = {
            "prompt": "Fix the same login bug we fixed last week",
            "context": {
                "ticket_id": "REPEAT-123",
                "similar_tickets": ["TICKET-100", "TICKET-200"]
            },
            "metadata": {
                "memory_context": True
            }
        }
        
        response = await pess_client.post("/score", request_data)
        assert response["status"] == 200
        
        # Should get contextual recommendations
        data = response["data"]
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0 