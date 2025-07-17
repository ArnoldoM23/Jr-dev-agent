"""
Integration tests for Template Intelligence service API endpoints.
"""

import pytest
import asyncio
import json
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


class TestTemplateIntelligenceServiceAPI:
    """Test Template Intelligence service API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, service_client_factory):
        """Test Template Intelligence service health check endpoint."""
        client = service_client_factory("template_intelligence")
        
        response = await client.get("/health")
        
        assert response["status"] == 200
        data = response["data"]
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "initialized" in data
        assert "total_templates" in data
        assert "template_names" in data
        
        assert data["status"] in ["healthy", "initializing"]
        assert data["service"] == "TemplateEngine"
        assert data["version"] == "1.0.0"
        
        if data["initialized"]:
            assert data["total_templates"] == 7  # 7 default templates
            assert len(data["template_names"]) == 7
    
    @pytest.mark.asyncio
    async def test_select_template_bug_ticket(self, service_client_factory):
        """Test template selection for bug ticket."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "BUG-123",
                "summary": "Fix login bug",
                "description": "Users are experiencing login issues and errors",
                "labels": ["bug", "critical", "fix"],
                "priority": "Critical"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "selected_template" in data
        assert "confidence_score" in data
        assert "ticket_id" in data
        assert "suggestions" in data
        
        assert data["selected_template"] == "bugfix"
        assert data["ticket_id"] == "BUG-123"
        assert 0.0 <= data["confidence_score"] <= 1.0
        
        # Check suggestions
        suggestions = data["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Bugfix should be top suggestion
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "bugfix"
        assert top_suggestion["score"] > 0
        assert "matched_keywords" in top_suggestion
        assert "bug" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_select_template_feature_ticket(self, service_client_factory):
        """Test template selection for feature ticket."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "FEAT-456",
                "summary": "Add new user authentication",
                "description": "Implement new OAuth2 authentication feature",
                "labels": ["feature", "enhancement", "new"],
                "priority": "High"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "feature"
        assert data["ticket_id"] == "FEAT-456"
        assert 0.0 <= data["confidence_score"] <= 1.0
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "feature"
        assert "feature" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_select_template_refactor_ticket(self, service_client_factory):
        """Test template selection for refactor ticket."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "REF-789",
                "summary": "Refactor authentication module",
                "description": "Cleanup and optimize authentication code structure",
                "labels": ["refactor", "improvement", "cleanup"],
                "priority": "Medium"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "refactor"
        assert data["ticket_id"] == "REF-789"
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "refactor"
        assert "refactor" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_select_template_version_upgrade(self, service_client_factory):
        """Test template selection for version upgrade ticket."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "UPG-101",
                "summary": "Upgrade React to v18",
                "description": "Update React dependency to latest version",
                "labels": ["upgrade", "dependency", "version"],
                "priority": "Medium"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "version_upgrade"
        assert data["ticket_id"] == "UPG-101"
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "version_upgrade"
        assert "upgrade" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_select_template_explicit_template(self, service_client_factory):
        """Test template selection with explicit template specified."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "EXPLICIT-123",
                "template_name": "test_generation",
                "summary": "Add unit tests",
                "description": "Add comprehensive unit tests for authentication module",
                "labels": ["testing"],
                "priority": "Low"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "test_generation"
        assert data["ticket_id"] == "EXPLICIT-123"
    
    @pytest.mark.asyncio
    async def test_select_template_mixed_keywords(self, service_client_factory):
        """Test template selection with mixed keywords."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "MIXED-456",
                "summary": "Fix bug and refactor code",
                "description": "Fix login bug and refactor authentication module",
                "labels": ["bug", "refactor", "fix", "improvement"],
                "priority": "High"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        # Should select based on scoring (could be bugfix or refactor)
        assert data["selected_template"] in ["bugfix", "refactor"]
        assert data["ticket_id"] == "MIXED-456"
        
        # Check that both templates appear in suggestions
        suggestions = data["suggestions"]
        template_names = [s["template_name"] for s in suggestions]
        assert "bugfix" in template_names
        assert "refactor" in template_names
    
    @pytest.mark.asyncio
    async def test_select_template_no_keywords(self, service_client_factory):
        """Test template selection with no matching keywords."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "NONE-789",
                "summary": "Random task",
                "description": "Some random task with no specific keywords",
                "labels": ["misc"],
                "priority": "Low"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        # Should default to feature template
        assert data["selected_template"] == "feature"
        assert data["ticket_id"] == "NONE-789"
    
    @pytest.mark.asyncio
    async def test_validate_template_valid_data(self, service_client_factory):
        """Test template validation with valid data."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "VALID-123",
                "summary": "Add new feature",
                "description": "Implement new user authentication feature",
                "acceptance_criteria": ["User can login", "JWT tokens work"],
                "files_affected": ["auth.py", "login.py"]
            }
        }
        
        response = await client.post("/validate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "valid" in data
        assert "missing_fields" in data
        assert "optional_fields" in data
        assert "template_info" in data
        
        assert data["valid"] is True
        assert len(data["missing_fields"]) == 0
        assert isinstance(data["optional_fields"], list)
        assert data["template_info"] is not None
    
    @pytest.mark.asyncio
    async def test_validate_template_missing_fields(self, service_client_factory):
        """Test template validation with missing required fields."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "template_name": "feature",
            "ticket_data": {
                "ticket_id": "INVALID-123"
                # Missing summary and description
            }
        }
        
        response = await client.post("/validate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["valid"] is False
        assert "summary" in data["missing_fields"]
        assert "description" in data["missing_fields"]
        assert data["template_info"] is not None
    
    @pytest.mark.asyncio
    async def test_validate_template_nonexistent(self, service_client_factory):
        """Test template validation with nonexistent template."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "template_name": "nonexistent",
            "ticket_data": {
                "ticket_id": "TEST-123",
                "summary": "Test ticket",
                "description": "Test description"
            }
        }
        
        response = await client.post("/validate", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["valid"] is False
        assert "error" in data
        assert "Template nonexistent not found" in data["error"]
    
    @pytest.mark.asyncio
    async def test_get_all_templates(self, service_client_factory):
        """Test getting all templates."""
        client = service_client_factory("template_intelligence")
        
        response = await client.get("/templates")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert "templates" in data
        assert "total" in data
        assert "categories" in data
        
        templates = data["templates"]
        assert isinstance(templates, dict)
        assert data["total"] == 7  # 7 default templates
        assert len(templates) == 7
        
        # Check that all expected templates are present
        expected_templates = [
            "feature", "bugfix", "refactor", "version_upgrade", 
            "config_update", "schema_change", "test_generation"
        ]
        for template_name in expected_templates:
            assert template_name in templates
            
            template = templates[template_name]
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "keywords" in template
            assert "required_fields" in template
            assert "optional_fields" in template
            assert "priority" in template
        
        # Check categories
        categories = data["categories"]
        assert isinstance(categories, list)
        expected_categories = ["configuration", "data", "development", "maintenance", "testing"]
        for category in expected_categories:
            assert category in categories
    
    @pytest.mark.asyncio
    async def test_get_specific_template(self, service_client_factory):
        """Test getting a specific template."""
        client = service_client_factory("template_intelligence")
        
        # Test getting feature template
        response = await client.get("/templates/feature")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["name"] == "feature"
        assert data["category"] == "development"
        assert data["priority"] == 1
        assert "keywords" in data
        assert "feature" in data["keywords"]
        assert "enhancement" in data["keywords"]
        
        # Test getting bugfix template
        response = await client.get("/templates/bugfix")
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["name"] == "bugfix"
        assert data["category"] == "maintenance"
        assert data["priority"] == 2
        assert "bug" in data["keywords"]
        assert "fix" in data["keywords"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, service_client_factory):
        """Test getting a nonexistent template."""
        client = service_client_factory("template_intelligence")
        
        response = await client.get("/templates/nonexistent")
        
        assert response["status"] == 404
        assert "Template 'nonexistent' not found" in response["data"]["detail"]
    
    @pytest.mark.asyncio
    async def test_template_categories_endpoint(self, service_client_factory):
        """Test template categories functionality."""
        client = service_client_factory("template_intelligence")
        
        # First get all templates to check categories
        response = await client.get("/templates")
        assert response["status"] == 200
        
        data = response["data"]
        categories = data["categories"]
        
        # Verify we have the expected categories
        expected_categories = ["configuration", "data", "development", "maintenance", "testing"]
        for category in expected_categories:
            assert category in categories
        
        # Categories should be sorted
        assert categories == sorted(categories)
    
    @pytest.mark.asyncio
    async def test_concurrent_template_selections(self, service_client_factory):
        """Test concurrent template selection requests."""
        client = service_client_factory("template_intelligence")
        
        # Create multiple concurrent requests
        requests = []
        for i in range(5):
            request_data = {
                "ticket_data": {
                    "ticket_id": f"CONCURRENT-{i}",
                    "summary": f"Fix bug {i}",
                    "description": f"Fix bug number {i}",
                    "labels": ["bug", "fix"]
                }
            }
            requests.append(client.post("/select", request_data))
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*requests)
        
        # Validate all responses
        for i, response in enumerate(responses):
            assert response["status"] == 200
            data = response["data"]
            assert data["selected_template"] == "bugfix"
            assert data["ticket_id"] == f"CONCURRENT-{i}"
    
    @pytest.mark.asyncio
    async def test_template_selection_validation_errors(self, service_client_factory):
        """Test validation errors for template selection."""
        client = service_client_factory("template_intelligence")
        
        # Test missing ticket_data
        invalid_request = {}
        
        response = await client.post("/select", invalid_request)
        assert response["status"] == 422  # Validation error
        
        # Test empty ticket_data
        invalid_request = {"ticket_data": {}}
        
        response = await client.post("/select", invalid_request)
        assert response["status"] == 200  # Should still work with empty data
        
        data = response["data"]
        assert data["selected_template"] == "feature"  # Default fallback
    
    @pytest.mark.asyncio
    async def test_template_validation_errors(self, service_client_factory):
        """Test validation errors for template validation."""
        client = service_client_factory("template_intelligence")
        
        # Test missing template_name
        invalid_request = {
            "ticket_data": {
                "ticket_id": "TEST-123",
                "summary": "Test",
                "description": "Test description"
            }
        }
        
        response = await client.post("/validate", invalid_request)
        assert response["status"] == 422  # Validation error
        
        # Test missing ticket_data
        invalid_request = {
            "template_name": "feature"
        }
        
        response = await client.post("/validate", invalid_request)
        assert response["status"] == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_template_schema_change_selection(self, service_client_factory):
        """Test template selection for schema change tickets."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "SCHEMA-123",
                "summary": "Database schema migration",
                "description": "Add new table for user preferences schema",
                "labels": ["schema", "database", "migration"],
                "priority": "Medium"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "schema_change"
        assert data["ticket_id"] == "SCHEMA-123"
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "schema_change"
        assert "schema" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_template_config_update_selection(self, service_client_factory):
        """Test template selection for configuration update tickets."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "CONFIG-456",
                "summary": "Update deployment configuration",
                "description": "Update production environment configuration settings",
                "labels": ["config", "deployment", "environment"],
                "priority": "High"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "config_update"
        assert data["ticket_id"] == "CONFIG-456"
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "config_update"
        assert "config" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_template_test_generation_selection(self, service_client_factory):
        """Test template selection for test generation tickets."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "TEST-789",
                "summary": "Add unit tests for authentication",
                "description": "Create comprehensive unit tests for authentication module",
                "labels": ["test", "testing", "unit", "coverage"],
                "priority": "Medium"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "test_generation"
        assert data["ticket_id"] == "TEST-789"
        
        # Check suggestions
        suggestions = data["suggestions"]
        top_suggestion = suggestions[0]
        assert top_suggestion["template_name"] == "test_generation"
        assert "test" in top_suggestion["matched_keywords"]
    
    @pytest.mark.asyncio
    async def test_template_confidence_scoring(self, service_client_factory):
        """Test template confidence scoring."""
        client = service_client_factory("template_intelligence")
        
        # Test with high confidence (many matching keywords)
        high_confidence_request = {
            "ticket_data": {
                "ticket_id": "HIGH-CONF",
                "summary": "Fix critical bug issue",
                "description": "Fix the critical bug causing system errors",
                "labels": ["bug", "fix", "critical", "issue", "error", "problem"],
                "priority": "Critical"
            }
        }
        
        response = await client.post("/select", high_confidence_request)
        assert response["status"] == 200
        
        data = response["data"]
        assert data["selected_template"] == "bugfix"
        high_confidence = data["confidence_score"]
        assert high_confidence > 0.6  # Should be relatively high
        
        # Test with low confidence (few matching keywords)
        low_confidence_request = {
            "ticket_data": {
                "ticket_id": "LOW-CONF",
                "summary": "Fix something",
                "description": "Fix some issue",
                "labels": ["fix"],
                "priority": "Low"
            }
        }
        
        response = await client.post("/select", low_confidence_request)
        assert response["status"] == 200
        
        data = response["data"]
        low_confidence = data["confidence_score"]
        
        # High confidence should be greater than low confidence
        assert high_confidence > low_confidence
    
    @pytest.mark.asyncio
    async def test_template_suggestions_ordering(self, service_client_factory):
        """Test that template suggestions are properly ordered by score."""
        client = service_client_factory("template_intelligence")
        
        request_data = {
            "ticket_data": {
                "ticket_id": "ORDERING-TEST",
                "summary": "Fix bug and refactor",
                "description": "Fix authentication bug and refactor authentication module",
                "labels": ["bug", "fix", "refactor", "authentication"],
                "priority": "High"
            }
        }
        
        response = await client.post("/select", request_data)
        
        assert response["status"] == 200
        
        data = response["data"]
        suggestions = data["suggestions"]
        
        # Check that suggestions are ordered by score (highest first)
        previous_score = float('inf')
        for suggestion in suggestions:
            current_score = suggestion["score"]
            assert current_score <= previous_score
            previous_score = current_score
    
    @pytest.mark.asyncio
    async def test_template_validation_all_templates(self, service_client_factory):
        """Test validation for all available templates."""
        client = service_client_factory("template_intelligence")
        
        # First get all templates
        templates_response = await client.get("/templates")
        assert templates_response["status"] == 200
        
        templates = templates_response["data"]["templates"]
        
        # Test validation for each template
        for template_name in templates.keys():
            valid_ticket_data = {
                "ticket_id": f"VALID-{template_name.upper()}",
                "summary": f"Test {template_name}",
                "description": f"Test description for {template_name}",
                "acceptance_criteria": ["Test criterion"],
                "files_affected": ["test.py"]
            }
            
            request_data = {
                "template_name": template_name,
                "ticket_data": valid_ticket_data
            }
            
            response = await client.post("/validate", request_data)
            assert response["status"] == 200
            
            data = response["data"]
            assert data["valid"] is True
            assert len(data["missing_fields"]) == 0
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self, service_client_factory):
        """Test error handling in the service."""
        client = service_client_factory("template_intelligence")
        
        # Test with invalid JSON
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8002/select",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 400
    
    @pytest.mark.asyncio
    async def test_service_initialization_status(self, service_client_factory):
        """Test that service is properly initialized."""
        client = service_client_factory("template_intelligence")
        
        # Check health first
        health_response = await client.get("/health")
        assert health_response["status"] == 200
        
        # If service is initialized, template operations should work
        if health_response["data"]["initialized"]:
            request_data = {
                "ticket_data": {
                    "ticket_id": "INIT-TEST",
                    "summary": "Test initialization",
                    "description": "Testing service initialization"
                }
            }
            
            response = await client.post("/select", request_data)
            assert response["status"] == 200
            assert response["data"]["selected_template"] == "feature"
    
    @pytest.mark.asyncio
    async def test_template_endpoint_404(self, service_client_factory):
        """Test 404 handling for template endpoints."""
        client = service_client_factory("template_intelligence")
        
        # Test invalid endpoint
        response = await client.get("/invalid-endpoint")
        assert response["status"] == 404
        
        # Test invalid template endpoint
        response = await client.get("/templates/invalid-template")
        assert response["status"] == 404 