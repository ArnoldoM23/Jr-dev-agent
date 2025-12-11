"""
End-to-end tests for complete Jr Dev Agent workflow.

These tests verify the complete workflow from ticket input to prompt generation
across all services.
"""

import pytest
import asyncio
from typing import Dict, Any


class TestCompleteWorkflow:
    """Test complete workflow integration."""
    
    @pytest.mark.asyncio
    async def test_complete_ticket_processing_workflow(self, service_client_factory):
        """Test the complete ticket processing workflow."""
        # This test verifies that all services work together properly
        
        # 1. Template Intelligence: Select template for ticket
        template_client = service_client_factory("template_intelligence")
        
        ticket_data = {
            "ticket_id": "E2E-123",
            "summary": "Fix authentication bug",
            "description": "Users cannot login due to JWT token validation issue",
            "labels": ["bug", "authentication", "critical"],
            "priority": "Critical",
            "acceptance_criteria": [
                "JWT token validation is fixed",
                "Users can login successfully",
                "All tests pass"
            ],
            "files_affected": [
                "src/auth/jwt.py",
                "src/auth/middleware.py",
                "tests/test_auth.py"
            ]
        }
        
        template_request = {"ticket_data": ticket_data}
        template_response = await template_client.post("/select", template_request)
        
        assert template_response["status"] == 200
        selected_template = template_response["data"]["selected_template"]
        assert selected_template == "bugfix"
        
        # 2. PromptBuilder: Generate prompt using selected template
        promptbuilder_client = service_client_factory("promptbuilder")
        
        prompt_request = {
            "template_name": selected_template,
            "ticket_data": ticket_data,
            "enrichment_data": {
                "context_enriched": True,
                "complexity_score": 7.5,
                "related_files": ["src/auth/utils.py"],
                "related_tickets": ["E2E-100", "E2E-101"]
            }
        }
        
        prompt_response = await promptbuilder_client.post("/generate", prompt_request)
        
        assert prompt_response["status"] == 200
        prompt_data = prompt_response["data"]
        assert prompt_data["success"] is True
        assert prompt_data["template_used"] == selected_template
        
        generated_prompt = prompt_data["prompt"]
        assert "E2E-123" in generated_prompt
        assert "Fix authentication bug" in generated_prompt
        assert "JWT token validation issue" in generated_prompt
        assert "🐛 Bug Fix Task:" in generated_prompt
        
        # 3. PESS: Score the generated prompt
        pess_client = service_client_factory("pess")
        
        pess_request = {
            "prompt": generated_prompt,
            "context": {
                "ticket_id": "E2E-123",
                "template_used": selected_template,
                "complexity": "medium"
            },
            "metadata": {
                "workflow_test": True,
                "generated_at": prompt_data["generated_at"]
            }
        }
        
        pess_response = await pess_client.post("/score", pess_request)
        
        assert pess_response["status"] == 200
        pess_data = pess_response["data"]
        assert 0.0 <= pess_data["overall_score"] <= 1.0
        assert 0.0 <= pess_data["confidence"] <= 1.0
        assert isinstance(pess_data["recommendations"], list)
        
        # The prompt should score reasonably well since it's structured
        assert pess_data["overall_score"] >= 0.6
        
        # 4. Verify all services are healthy
        services = ["template_intelligence", "promptbuilder", "pess"]
        for service_name in services:
            client = service_client_factory(service_name)
            health_response = await client.get("/health")
            assert health_response["status"] == 200
            assert health_response["data"]["status"] in ["healthy", "initializing"]
    
    @pytest.mark.asyncio
    async def test_feature_development_workflow(self, service_client_factory):
        """Test workflow for feature development ticket."""
        
        # Feature ticket data
        feature_ticket = {
            "ticket_id": "FEAT-E2E-456",
            "summary": "Add OAuth2 authentication",
            "description": "Implement OAuth2 authentication with Google and GitHub providers",
            "labels": ["feature", "authentication", "oauth2"],
            "priority": "High",
            "acceptance_criteria": [
                "Google OAuth2 integration works",
                "GitHub OAuth2 integration works",
                "User can login with both providers",
                "Proper error handling for failed logins"
            ],
            "files_affected": [
                "src/auth/oauth2.py",
                "src/auth/providers/google.py",
                "src/auth/providers/github.py",
                "tests/test_oauth2.py"
            ]
        }
        
        # 1. Template selection
        template_client = service_client_factory("template_intelligence")
        template_response = await template_client.post("/select", {"ticket_data": feature_ticket})
        
        assert template_response["status"] == 200
        assert template_response["data"]["selected_template"] == "feature"
        
        # 2. Prompt generation
        promptbuilder_client = service_client_factory("promptbuilder")
        prompt_response = await promptbuilder_client.post("/generate", {
            "template_name": "feature",
            "ticket_data": feature_ticket
        })
        
        assert prompt_response["status"] == 200
        prompt_data = prompt_response["data"]
        generated_prompt = prompt_data["prompt"]
        
        # Verify feature-specific content
        assert "🎯 Development Task:" in generated_prompt
        assert "FEAT-E2E-456" in generated_prompt
        assert "Add OAuth2 authentication" in generated_prompt
        assert "Google OAuth2 integration works" in generated_prompt
        
        # 3. PESS scoring
        pess_client = service_client_factory("pess")
        pess_response = await pess_client.post("/score", {
            "prompt": generated_prompt,
            "context": {"ticket_id": "FEAT-E2E-456"},
            "metadata": {"test_type": "feature_workflow"}
        })
        
        assert pess_response["status"] == 200
        pess_data = pess_response["data"]
        
        # Feature prompts should score well due to detailed requirements
        assert pess_data["overall_score"] >= 0.7
        assert pess_data["dimensional_scores"]["clarity"] >= 0.6
        assert pess_data["dimensional_scores"]["completeness"] >= 0.6
    
    @pytest.mark.asyncio
    async def test_refactor_workflow(self, service_client_factory):
        """Test workflow for refactoring ticket."""
        
        refactor_ticket = {
            "ticket_id": "REF-E2E-789",
            "summary": "Refactor authentication module",
            "description": "Improve code structure and performance of authentication module",
            "labels": ["refactor", "performance", "cleanup"],
            "priority": "Medium",
            "acceptance_criteria": [
                "Code is more readable and maintainable",
                "Performance is improved by at least 20%",
                "All existing tests still pass",
                "New unit tests are added for refactored code"
            ],
            "files_affected": [
                "src/auth/service.py",
                "src/auth/models.py",
                "src/auth/utils.py",
                "tests/test_auth_refactor.py"
            ]
        }
        
        # Complete workflow
        template_client = service_client_factory("template_intelligence")
        template_response = await template_client.post("/select", {"ticket_data": refactor_ticket})
        assert template_response["status"] == 200
        assert template_response["data"]["selected_template"] == "refactor"
        
        promptbuilder_client = service_client_factory("promptbuilder")
        prompt_response = await promptbuilder_client.post("/generate", {
            "template_name": "refactor",
            "ticket_data": refactor_ticket
        })
        assert prompt_response["status"] == 200
        
        generated_prompt = prompt_response["data"]["prompt"]
        assert "🔄 Refactoring Task:" in generated_prompt
        assert "SOLID principles" in generated_prompt
        
        pess_client = service_client_factory("pess")
        pess_response = await pess_client.post("/score", {
            "prompt": generated_prompt,
            "context": {"ticket_id": "REF-E2E-789"},
            "metadata": {"test_type": "refactor_workflow"}
        })
        assert pess_response["status"] == 200
        assert pess_response["data"]["overall_score"] >= 0.6
    
    @pytest.mark.asyncio
    async def test_template_validation_workflow(self, service_client_factory):
        """Test template validation workflow."""
        
        template_client = service_client_factory("template_intelligence")
        
        # Test validation for different templates
        templates_to_test = ["feature", "bugfix", "refactor"]
        
        for template_name in templates_to_test:
            # Valid ticket data
            valid_ticket = {
                "ticket_id": f"VALID-{template_name.upper()}",
                "summary": f"Test {template_name}",
                "description": f"Test description for {template_name}",
                "acceptance_criteria": ["Test criterion"],
                "files_affected": ["test.py"]
            }
            
            validation_response = await template_client.post("/validate", {
                "template_name": template_name,
                "ticket_data": valid_ticket
            })
            
            assert validation_response["status"] == 200
            assert validation_response["data"]["valid"] is True
            
            # Invalid ticket data (missing required fields)
            invalid_ticket = {
                "ticket_id": f"INVALID-{template_name.upper()}"
                # Missing summary and description
            }
            
            validation_response = await template_client.post("/validate", {
                "template_name": template_name,
                "ticket_data": invalid_ticket
            })
            
            assert validation_response["status"] == 200
            assert validation_response["data"]["valid"] is False
            assert "summary" in validation_response["data"]["missing_fields"]
            assert "description" in validation_response["data"]["missing_fields"]
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing(self, service_client_factory):
        """Test concurrent processing of multiple tickets."""
        
        # Create multiple tickets to process concurrently
        tickets = [
            {
                "ticket_id": f"CONCURRENT-{i}",
                "summary": f"Task {i}",
                "description": f"Description for task {i}",
                "labels": ["bug" if i % 2 == 0 else "feature"],
                "priority": "Medium"
            }
            for i in range(5)
        ]
        
        # Process all tickets concurrently
        template_client = service_client_factory("template_intelligence")
        promptbuilder_client = service_client_factory("promptbuilder")
        
        async def process_ticket(ticket):
            # Template selection
            template_response = await template_client.post("/select", {"ticket_data": ticket})
            assert template_response["status"] == 200
            
            selected_template = template_response["data"]["selected_template"]
            
            # Prompt generation
            prompt_response = await promptbuilder_client.post("/generate", {
                "template_name": selected_template,
                "ticket_data": ticket
            })
            assert prompt_response["status"] == 200
            
            return {
                "ticket_id": ticket["ticket_id"],
                "template": selected_template,
                "prompt": prompt_response["data"]["prompt"]
            }
        
        # Process all tickets concurrently
        tasks = [process_ticket(ticket) for ticket in tickets]
        results = await asyncio.gather(*tasks)
        
        # Verify all tickets were processed
        assert len(results) == 5
        
        for i, result in enumerate(results):
            assert result["ticket_id"] == f"CONCURRENT-{i}"
            assert result["template"] in ["bugfix", "feature"]
            assert f"CONCURRENT-{i}" in result["prompt"]
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, service_client_factory):
        """Test error handling across the workflow."""
        
        # Test with invalid template name
        promptbuilder_client = service_client_factory("promptbuilder")
        
        invalid_template_response = await promptbuilder_client.post("/generate", {
            "template_name": "invalid_template",
            "ticket_data": {
                "ticket_id": "ERROR-TEST",
                "summary": "Test error handling",
                "description": "Test description"
            }
        })
        
        # Should still work (fallback to feature template)
        assert invalid_template_response["status"] == 200
        assert invalid_template_response["data"]["success"] is True
        
        # Test with missing required fields
        template_client = service_client_factory("template_intelligence")
        
        validation_response = await template_client.post("/validate", {
            "template_name": "feature",
            "ticket_data": {}  # Empty ticket data
        })
        
        assert validation_response["status"] == 200
        assert validation_response["data"]["valid"] is False
        assert len(validation_response["data"]["missing_fields"]) > 0
    
    @pytest.mark.asyncio
    async def test_service_dependencies(self, service_client_factory):
        """Test service dependencies and integration points."""
        
        # Verify that services can communicate and work together
        services = {
            "template_intelligence": service_client_factory("template_intelligence"),
            "promptbuilder": service_client_factory("promptbuilder"),
            "pess": service_client_factory("pess")
        }
        
        # Check that all services are healthy
        for service_name, client in services.items():
            health_response = await client.get("/health")
            assert health_response["status"] == 200
            
            health_data = health_response["data"]
            assert health_data["status"] in ["healthy", "initializing"]
            
            # Verify service-specific health indicators
            if service_name == "template_intelligence":
                assert "total_templates" in health_data
                assert health_data["total_templates"] > 0
            
            if service_name == "promptbuilder":
                assert "service" in health_data
                assert health_data["service"] == "PromptBuilder"
            
            if service_name == "pess":
                assert "service" in health_data
        
        # Test data flow between services
        ticket_data = {
            "ticket_id": "DEPENDENCY-TEST",
            "summary": "Test service dependencies",
            "description": "Testing how services work together",
            "labels": ["integration", "test"]
        }
        
        # Template Intelligence -> PromptBuilder -> PESS
        template_response = await services["template_intelligence"].post("/select", {"ticket_data": ticket_data})
        assert template_response["status"] == 200
        
        prompt_response = await services["promptbuilder"].post("/generate", {
            "template_name": template_response["data"]["selected_template"],
            "ticket_data": ticket_data
        })
        assert prompt_response["status"] == 200
        
        pess_response = await services["pess"].post("/score", {
            "prompt": prompt_response["data"]["prompt"],
            "context": {"ticket_id": "DEPENDENCY-TEST"},
            "metadata": {"test_type": "dependency_test"}
        })
        assert pess_response["status"] == 200
        
        # Verify data consistency across services
        assert template_response["data"]["ticket_id"] == "DEPENDENCY-TEST"
        assert prompt_response["data"]["ticket_id"] == "DEPENDENCY-TEST"
        assert "DEPENDENCY-TEST" in prompt_response["data"]["prompt"] 