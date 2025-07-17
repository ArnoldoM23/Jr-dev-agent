"""
Integration tests for PromptBuilder service API endpoints.
"""

import pytest
import asyncio
import json
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


class TestPromptBuilderServiceAPI:
    """Test PromptBuilder service API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, service_client_factory):
        """Test PromptBuilder service health check endpoint."""
        client = service_client_factory("promptbuilder")
        
        response = await client.get("/health")
        
        assert response["status"] == 200
        data = response["data"]
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "initialized" in data
        
        assert data["status"] in ["healthy", "initializing"]
        assert data["service"] == "PromptBuilder"
        assert data["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_generate_feature_prompt(self, service_client_factory):
        """Test feature prompt generation endpoint."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "FEAT-123",
                "summary": "Add user authentication",
                "description": "Implement JWT-based authentication system",
                "priority": "High",
                "feature": "Authentication",
                "assignee": "john.doe",
                "acceptance_criteria": [
                    "User can login with email and password",
                    "JWT tokens are generated on successful login",
                    "Protected routes require valid tokens"
                ],
                "files_affected": [
                    "src/auth/login.py",
                    "src/auth/middleware.py",
                    "tests/test_auth.py"
                ],
                "labels": ["feature", "backend", "security"],
                "components": ["authentication", "api"]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "prompt" in data
        assert "template_used" in data
        assert "ticket_id" in data
        assert "generated_at" in data
        assert "success" in data
        
        assert data["template_used"] == "feature"
        assert data["ticket_id"] == "FEAT-123"
        assert data["success"] is True
        
        # Check prompt content
        prompt = data["prompt"]
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "FEAT-123" in prompt
        assert "Add user authentication" in prompt
        assert "JWT-based authentication system" in prompt
        assert "# 🎯 Development Task:" in prompt
        assert "## 📋 Ticket Information" in prompt
        assert "## 🤖 Instructions for GitHub Copilot" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_bugfix_prompt(self, service_client_factory):
        """Test bugfix prompt generation endpoint."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "bugfix",
            "ticket_data": {
                "ticket_id": "BUG-456",
                "summary": "Fix login validation error",
                "description": "Users can login with invalid email formats",
                "priority": "Critical",
                "feature": "Authentication",
                "assignee": "jane.smith",
                "acceptance_criteria": [
                    "Email format validation is enforced",
                    "Invalid emails show appropriate error message",
                    "Existing valid logins still work"
                ],
                "files_affected": [
                    "src/auth/validators.py",
                    "src/auth/login.py",
                    "tests/test_validation.py"
                ]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["template_used"] == "bugfix"
        assert data["ticket_id"] == "BUG-456"
        assert data["success"] is True
        
        # Check prompt content
        prompt = data["prompt"]
        assert "BUG-456" in prompt
        assert "Fix login validation error" in prompt
        assert "# 🐛 Bug Fix Task:" in prompt
        assert "## 📝 Bug Description" in prompt
        assert "## 🔧 Bug Fix Guidelines" in prompt
        assert "minimal, targeted changes" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_refactor_prompt(self, service_client_factory):
        """Test refactor prompt generation endpoint."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "refactor",
            "ticket_data": {
                "ticket_id": "REF-789",
                "summary": "Refactor authentication module",
                "description": "Improve code structure and performance of auth module",
                "priority": "Medium",
                "feature": "Authentication",
                "assignee": "bob.johnson",
                "acceptance_criteria": [
                    "Code is more maintainable and readable",
                    "Performance is improved by 20%",
                    "All existing tests still pass"
                ],
                "files_affected": [
                    "src/auth/service.py",
                    "src/auth/models.py",
                    "src/auth/utils.py"
                ]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["template_used"] == "refactor"
        assert data["ticket_id"] == "REF-789"
        assert data["success"] is True
        
        # Check prompt content
        prompt = data["prompt"]
        assert "REF-789" in prompt
        assert "Refactor authentication module" in prompt
        assert "# 🔄 Refactoring Task:" in prompt
        assert "## 📝 Refactoring Description" in prompt
        assert "## 🔧 Refactoring Guidelines" in prompt
        assert "SOLID principles" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_prompt_with_enrichment_data(self, service_client_factory):
        """Test prompt generation with enrichment data."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "FEAT-456",
                "summary": "Add payment processing",
                "description": "Implement payment processing with Stripe",
                "priority": "High",
                "feature": "Payments",
                "assignee": "alice.cooper",
                "acceptance_criteria": ["Process credit card payments"],
                "files_affected": ["src/payments/stripe.py"]
            },
            "enrichment_data": {
                "context_enriched": True,
                "complexity_score": 8.5,
                "related_files": ["src/payments/models.py", "src/payments/utils.py"],
                "related_tickets": ["FEAT-123", "BUG-789"]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["success"] is True
        
        # Check that enrichment data is included in prompt
        prompt = data["prompt"]
        assert "## 🧠 Context & Insights" in prompt
        assert "8.5" in prompt  # complexity score
        assert "src/payments/models.py" in prompt  # related files
        assert "FEAT-123" in prompt  # related tickets
    
    @pytest.mark.asyncio
    async def test_generate_prompt_unknown_template(self, service_client_factory):
        """Test prompt generation with unknown template."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "unknown_template",
            "ticket_data": {
                "ticket_id": "UNKNOWN-123",
                "summary": "Test unknown template",
                "description": "Testing unknown template handling",
                "acceptance_criteria": ["Should work"],
                "files_affected": ["test.py"]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        # Should still work (fallback to feature template)
        assert response["status"] == 200
        
        data = response["data"]
        assert data["template_used"] == "unknown_template"
        assert data["success"] is True
        
        # Should use feature template as fallback
        prompt = data["prompt"]
        assert "# 🎯 Development Task:" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_prompt_validation_errors(self, service_client_factory):
        """Test validation errors for /generate endpoint."""
        client = service_client_factory("promptbuilder")
        
        # Test missing template_name
        invalid_request = {
            "ticket_data": {
                "ticket_id": "TEST-123",
                "summary": "Test",
                "description": "Test description"
            }
        }
        
        response = await client.post("/generate", invalid_request)
        assert response["status"] == 422  # Validation error
        
        # Test missing ticket_data
        invalid_request = {
            "template_name": "feature"
        }
        
        response = await client.post("/generate", invalid_request)
        assert response["status"] == 422  # Validation error
        
        # Test empty ticket_data
        invalid_request = {
            "template_name": "feature",
            "ticket_data": {}
        }
        
        response = await client.post("/generate", invalid_request)
        # Should work with empty ticket_data (will use defaults)
        assert response["status"] in [200, 500]  # Either works or internal error
    
    @pytest.mark.asyncio
    async def test_get_supported_templates(self, service_client_factory):
        """Test the /templates endpoint."""
        client = service_client_factory("promptbuilder")
        
        response = await client.get("/templates")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "templates" in data
        assert "service" in data
        assert "version" in data
        
        assert data["templates"] == ["feature", "bugfix", "refactor"]
        assert data["service"] == "PromptBuilder"
        assert data["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_get_status(self, service_client_factory):
        """Test the /status endpoint."""
        client = service_client_factory("promptbuilder")
        
        response = await client.get("/status")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "initialized" in data
        assert "service" in data
        assert "version" in data
        assert "supported_templates" in data
        
        assert data["service"] == "PromptBuilder"
        assert data["version"] == "1.0.0"
        assert data["supported_templates"] == ["feature", "bugfix", "refactor"]
    
    @pytest.mark.asyncio
    async def test_concurrent_prompt_generation(self, service_client_factory):
        """Test handling of concurrent prompt generation requests."""
        client = service_client_factory("promptbuilder")
        
        # Create multiple concurrent requests
        requests = []
        for i in range(5):
            request_data = {
                "template_name": "feature",
                "ticket_data": {
                    "ticket_id": f"CONCURRENT-{i}",
                    "summary": f"Concurrent task {i}",
                    "description": f"Testing concurrent generation {i}",
                    "acceptance_criteria": [f"Complete task {i}"],
                    "files_affected": [f"file_{i}.py"]
                }
            }
            requests.append(client.post("/generate", request_data))
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*requests)
        
        # Validate all responses
        for i, response in enumerate(responses):
            assert response["status"] == 200
            data = response["data"]
            assert data["success"] is True
            assert f"CONCURRENT-{i}" in data["prompt"]
    
    @pytest.mark.asyncio
    async def test_large_ticket_data_handling(self, service_client_factory):
        """Test handling of large ticket data."""
        client = service_client_factory("promptbuilder")
        
        # Create a large ticket with many criteria and files
        large_criteria = [f"Acceptance criterion {i}" for i in range(50)]
        large_files = [f"src/module_{i}/file_{i}.py" for i in range(30)]
        large_labels = [f"label_{i}" for i in range(20)]
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "LARGE-123",
                "summary": "Large ticket with many requirements",
                "description": "This is a large ticket with many requirements " * 100,
                "priority": "High",
                "feature": "LargeFeature",
                "assignee": "developer.large",
                "acceptance_criteria": large_criteria,
                "files_affected": large_files,
                "labels": large_labels,
                "components": ["comp1", "comp2", "comp3"]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        data = response["data"]
        assert data["success"] is True
        
        # Check that large data is handled properly
        prompt = data["prompt"]
        assert "LARGE-123" in prompt
        assert "Acceptance criterion 0" in prompt
        assert "Acceptance criterion 49" in prompt
        assert "src/module_0/file_0.py" in prompt
        assert "src/module_29/file_29.py" in prompt
    
    @pytest.mark.asyncio
    async def test_minimal_ticket_data_handling(self, service_client_factory):
        """Test handling of minimal ticket data."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "MINIMAL-123",
                "summary": "Minimal ticket",
                "description": "Basic description"
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        data = response["data"]
        assert data["success"] is True
        
        prompt = data["prompt"]
        assert "MINIMAL-123" in prompt
        assert "Minimal ticket" in prompt
        assert "Basic description" in prompt
        
        # Check that defaults are used
        assert "Medium" in prompt  # default priority
        assert "unknown" in prompt  # default feature
        assert "unassigned" in prompt  # default assignee
    
    @pytest.mark.asyncio
    async def test_special_characters_in_ticket_data(self, service_client_factory):
        """Test handling of special characters in ticket data."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "SPECIAL-123",
                "summary": "Test with special chars: @#$%^&*()[]{}",
                "description": "Description with unicode: αβγδε and emojis: 🚀🎯🔥",
                "priority": "High",
                "acceptance_criteria": [
                    "Handle special chars: <>\"'&",
                    "Process unicode: ñáéíóú",
                    "Support emojis: 😀😃😄"
                ],
                "files_affected": [
                    "src/special-chars.py",
                    "src/unicode_file.py"
                ]
            }
        }
        
        response = await client.post("/generate", request_data)
        
        assert response["status"] == 200
        data = response["data"]
        assert data["success"] is True
        
        prompt = data["prompt"]
        assert "SPECIAL-123" in prompt
        assert "@#$%^&*()" in prompt
        assert "αβγδε" in prompt
        assert "🚀🎯🔥" in prompt
        assert "ñáéíóú" in prompt
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_json(self, service_client_factory):
        """Test error handling with invalid JSON."""
        import aiohttp
        
        # Test with malformed JSON
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/generate",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 400
    
    @pytest.mark.asyncio
    async def test_service_initialization_status(self, service_client_factory):
        """Test that service is properly initialized."""
        client = service_client_factory("promptbuilder")
        
        # Check health first
        health_response = await client.get("/health")
        assert health_response["status"] == 200
        
        # If service is initialized, prompt generation should work
        if health_response["data"]["initialized"]:
            request_data = {
                "template_name": "feature",
                "ticket_data": {
                    "ticket_id": "INIT-TEST",
                    "summary": "Test initialization",
                    "description": "Testing service initialization"
                }
            }
            
            response = await client.post("/generate", request_data)
            assert response["status"] == 200
            assert response["data"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_response_time_performance(self, service_client_factory):
        """Test response time performance."""
        client = service_client_factory("promptbuilder")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "PERF-TEST",
                "summary": "Performance test",
                "description": "Testing response time performance",
                "acceptance_criteria": ["Should respond quickly"],
                "files_affected": ["src/performance.py"]
            }
        }
        
        import time
        start_time = time.time()
        
        response = await client.post("/generate", request_data)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response["status"] == 200
        assert response["data"]["success"] is True
        
        # Response should be reasonably fast (less than 5 seconds)
        assert response_time < 5.0
    
    @pytest.mark.asyncio
    async def test_different_template_combinations(self, service_client_factory):
        """Test different template types with various ticket data combinations."""
        client = service_client_factory("promptbuilder")
        
        test_cases = [
            ("feature", "FEAT-COMBO-1", "Add new feature"),
            ("bugfix", "BUG-COMBO-2", "Fix existing bug"),
            ("refactor", "REF-COMBO-3", "Refactor existing code")
        ]
        
        for template_name, ticket_id, summary in test_cases:
            request_data = {
                "template_name": template_name,
                "ticket_data": {
                    "ticket_id": ticket_id,
                    "summary": summary,
                    "description": f"Testing {template_name} template",
                    "acceptance_criteria": [f"Should handle {template_name}"],
                    "files_affected": [f"src/{template_name}_file.py"]
                }
            }
            
            response = await client.post("/generate", request_data)
            
            assert response["status"] == 200
            data = response["data"]
            assert data["success"] is True
            assert data["template_used"] == template_name
            assert data["ticket_id"] == ticket_id
            
            prompt = data["prompt"]
            assert ticket_id in prompt
            assert summary in prompt
    
    @pytest.mark.asyncio
    async def test_enrichment_data_edge_cases(self, service_client_factory):
        """Test enrichment data edge cases."""
        client = service_client_factory("promptbuilder")
        
        # Test with empty enrichment data
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "ENRICH-EMPTY",
                "summary": "Empty enrichment test",
                "description": "Testing empty enrichment data"
            },
            "enrichment_data": {}
        }
        
        response = await client.post("/generate", request_data)
        assert response["status"] == 200
        assert response["data"]["success"] is True
        
        # Test with null enrichment data
        request_data["enrichment_data"] = None
        response = await client.post("/generate", request_data)
        assert response["status"] == 200
        assert response["data"]["success"] is True
        
        # Test with context_enriched=False
        request_data["enrichment_data"] = {"context_enriched": False}
        response = await client.post("/generate", request_data)
        assert response["status"] == 200
        assert response["data"]["success"] is True
        
        # Prompt should not include enrichment section
        prompt = response["data"]["prompt"]
        assert "## 🧠 Context & Insights" not in prompt 