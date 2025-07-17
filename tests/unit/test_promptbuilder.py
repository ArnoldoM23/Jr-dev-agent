"""
Unit tests for PromptBuilder service core functionality.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../promptbuilder'))

from promptbuilder.service import PromptBuilder, promptbuilder


class TestPromptBuilderCore:
    """Test PromptBuilder core functionality."""
    
    def test_promptbuilder_initialization(self):
        """Test PromptBuilder initialization."""
        builder = PromptBuilder()
        assert builder is not None
        assert not builder.initialized
        assert hasattr(builder, 'logger')
    
    @pytest.mark.asyncio
    async def test_initialize_method(self):
        """Test service initialization."""
        builder = PromptBuilder()
        await builder.initialize()
        
        assert builder.initialized
        
        # Cleanup
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test service cleanup."""
        builder = PromptBuilder()
        await builder.initialize()
        assert builder.initialized
        
        await builder.cleanup()
        assert not builder.initialized
    
    def test_get_status(self):
        """Test status reporting."""
        builder = PromptBuilder()
        status = builder.get_status()
        
        assert isinstance(status, dict)
        assert "initialized" in status
        assert "service" in status
        assert "version" in status
        assert "supported_templates" in status
        
        assert status["service"] == "PromptBuilder"
        assert status["version"] == "1.0.0"
        assert status["supported_templates"] == ["feature", "bugfix", "refactor"]
    
    @pytest.mark.asyncio
    async def test_generate_feature_prompt(self):
        """Test feature prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
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
        
        prompt = await builder.generate_prompt("feature", ticket_data)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key information is included
        assert "FEAT-123" in prompt
        assert "Add user authentication" in prompt
        assert "JWT-based authentication system" in prompt
        assert "High" in prompt
        assert "User can login with email and password" in prompt
        assert "src/auth/login.py" in prompt
        assert "feature" in prompt
        assert "authentication" in prompt
        
        # Check structural elements
        assert "# 🎯 Development Task:" in prompt
        assert "## 📋 Ticket Information" in prompt
        assert "## 📝 Description" in prompt
        assert "## ✅ Acceptance Criteria" in prompt
        assert "## 📁 Files to Modify" in prompt
        assert "## 🤖 Instructions for GitHub Copilot" in prompt
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_generate_bugfix_prompt(self):
        """Test bugfix prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
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
        
        prompt = await builder.generate_prompt("bugfix", ticket_data)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key information is included
        assert "BUG-456" in prompt
        assert "Fix login validation error" in prompt
        assert "Users can login with invalid email formats" in prompt
        assert "Critical" in prompt
        assert "Email format validation is enforced" in prompt
        assert "src/auth/validators.py" in prompt
        
        # Check structural elements specific to bugfix
        assert "# 🐛 Bug Fix Task:" in prompt
        assert "## 📝 Bug Description" in prompt
        assert "## ✅ Fix Criteria" in prompt
        assert "## 📁 Files to Investigate/Fix" in prompt
        assert "## 🔧 Bug Fix Guidelines" in prompt
        assert "minimal, targeted changes" in prompt
        assert "regression tests" in prompt
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_generate_refactor_prompt(self):
        """Test refactor prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
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
        
        prompt = await builder.generate_prompt("refactor", ticket_data)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key information is included
        assert "REF-789" in prompt
        assert "Refactor authentication module" in prompt
        assert "Improve code structure and performance" in prompt
        assert "Medium" in prompt
        assert "Code is more maintainable and readable" in prompt
        assert "src/auth/service.py" in prompt
        
        # Check structural elements specific to refactor
        assert "# 🔄 Refactoring Task:" in prompt
        assert "## 📝 Refactoring Description" in prompt
        assert "## ✅ Refactoring Goals" in prompt
        assert "## 📁 Files to Refactor" in prompt
        assert "## 🔧 Refactoring Guidelines" in prompt
        assert "Maintain existing functionality" in prompt
        assert "SOLID principles" in prompt
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_generate_prompt_with_enrichment_data(self):
        """Test prompt generation with enrichment data."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
            "ticket_id": "FEAT-456",
            "summary": "Add payment processing",
            "description": "Implement payment processing with Stripe",
            "priority": "High",
            "feature": "Payments",
            "assignee": "alice.cooper",
            "acceptance_criteria": ["Process credit card payments"],
            "files_affected": ["src/payments/stripe.py"]
        }
        
        enrichment_data = {
            "context_enriched": True,
            "complexity_score": 8.5,
            "related_files": ["src/payments/models.py", "src/payments/utils.py"],
            "related_tickets": ["FEAT-123", "BUG-789"]
        }
        
        prompt = await builder.generate_prompt("feature", ticket_data, enrichment_data)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that enrichment data is included
        assert "## 🧠 Context & Insights" in prompt
        assert "8.5" in prompt  # complexity score
        assert "src/payments/models.py" in prompt  # related files
        assert "FEAT-123" in prompt  # related tickets
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_generate_prompt_unknown_template(self):
        """Test prompt generation with unknown template falls back to feature."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
            "ticket_id": "UNKNOWN-123",
            "summary": "Test unknown template",
            "description": "Testing unknown template handling",
            "acceptance_criteria": ["Should work"],
            "files_affected": ["test.py"]
        }
        
        with patch.object(builder, 'logger') as mock_logger:
            prompt = await builder.generate_prompt("unknown_template", ticket_data)
            
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            
            # Should use feature template as fallback
            assert "# 🎯 Development Task:" in prompt
            
            # Should log warning about unknown template
            mock_logger.warning.assert_called_once()
            assert "Unknown template unknown_template" in mock_logger.warning.call_args[0][0]
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_generate_prompt_error_handling(self):
        """Test error handling in prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        # Test with invalid ticket data
        invalid_ticket_data = None
        
        with pytest.raises(Exception):
            await builder.generate_prompt("feature", invalid_ticket_data)
        
        await builder.cleanup()
    
    def test_generate_feature_prompt_with_string_criteria(self):
        """Test feature prompt generation with string acceptance criteria."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "FEAT-STRING",
            "summary": "Test with string criteria",
            "description": "Testing string criteria handling",
            "acceptance_criteria": "Single string criteria",
            "files_affected": "single_file.py"
        }
        
        prompt = builder._generate_feature_prompt(ticket_data)
        
        assert isinstance(prompt, str)
        assert "Single string criteria" in prompt
        assert "single_file.py" in prompt
    
    def test_generate_feature_prompt_with_minimal_data(self):
        """Test feature prompt generation with minimal ticket data."""
        builder = PromptBuilder()
        
        minimal_ticket_data = {
            "ticket_id": "MINIMAL-123",
            "summary": "Minimal ticket",
            "description": "Basic description"
        }
        
        prompt = builder._generate_feature_prompt(minimal_ticket_data)
        
        assert isinstance(prompt, str)
        assert "MINIMAL-123" in prompt
        assert "Minimal ticket" in prompt
        assert "Basic description" in prompt
        
        # Check default values are handled
        assert "Medium" in prompt  # default priority
        assert "unknown" in prompt  # default feature
        assert "unassigned" in prompt  # default assignee
    
    def test_generate_bugfix_prompt_structure(self):
        """Test bugfix prompt structure and content."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "BUG-STRUCT",
            "summary": "Structure test bug",
            "description": "Testing structure",
            "acceptance_criteria": ["Fix the bug"],
            "files_affected": ["bug_file.py"]
        }
        
        prompt = builder._generate_bugfix_prompt(ticket_data)
        
        # Check bugfix-specific elements
        assert "🐛 Bug Fix Task:" in prompt
        assert "Bug Description" in prompt
        assert "Fix Criteria" in prompt
        assert "Files to Investigate/Fix" in prompt
        assert "Make minimal, targeted changes" in prompt
        assert "Add regression tests" in prompt
        assert "Reproduce the bug locally" in prompt
    
    def test_generate_refactor_prompt_structure(self):
        """Test refactor prompt structure and content."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "REF-STRUCT",
            "summary": "Structure test refactor",
            "description": "Testing structure",
            "acceptance_criteria": ["Improve code"],
            "files_affected": ["refactor_file.py"]
        }
        
        prompt = builder._generate_refactor_prompt(ticket_data)
        
        # Check refactor-specific elements
        assert "🔄 Refactoring Task:" in prompt
        assert "Refactoring Description" in prompt
        assert "Refactoring Goals" in prompt
        assert "Files to Refactor" in prompt
        assert "Maintain existing functionality" in prompt
        assert "SOLID principles" in prompt
        assert "Understand current code structure" in prompt
    
    def test_global_promptbuilder_instance(self):
        """Test that global promptbuilder instance exists."""
        assert promptbuilder is not None
        assert isinstance(promptbuilder, PromptBuilder)
    
    @pytest.mark.asyncio
    async def test_concurrent_prompt_generation(self):
        """Test concurrent prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            ticket_data = {
                "ticket_id": f"CONCURRENT-{i}",
                "summary": f"Concurrent task {i}",
                "description": f"Testing concurrent generation {i}",
                "acceptance_criteria": [f"Complete task {i}"],
                "files_affected": [f"file_{i}.py"]
            }
            tasks.append(builder.generate_prompt("feature", ticket_data))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        assert len(results) == 5
        for i, prompt in enumerate(results):
            assert isinstance(prompt, str)
            assert f"CONCURRENT-{i}" in prompt
            assert f"Concurrent task {i}" in prompt
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_prompt_generation_logging(self):
        """Test logging during prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        ticket_data = {
            "ticket_id": "LOG-TEST",
            "summary": "Logging test",
            "description": "Testing logging",
            "acceptance_criteria": ["Log properly"],
            "files_affected": ["log_file.py"]
        }
        
        with patch.object(builder, 'logger') as mock_logger:
            prompt = await builder.generate_prompt("feature", ticket_data)
            
            # Check that info logs were called
            mock_logger.info.assert_called()
            
            # Check specific log messages
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Generating prompt for ticket LOG-TEST" in msg for msg in log_calls)
            assert any("Successfully generated prompt for LOG-TEST" in msg for msg in log_calls)
        
        await builder.cleanup()
    
    @pytest.mark.asyncio
    async def test_prompt_generation_with_exception(self):
        """Test exception handling in prompt generation."""
        builder = PromptBuilder()
        await builder.initialize()
        
        # Mock an exception in the template generation
        with patch.object(builder, '_generate_feature_prompt', side_effect=Exception("Test error")):
            with patch.object(builder, 'logger') as mock_logger:
                with pytest.raises(Exception):
                    await builder.generate_prompt("feature", {"ticket_id": "ERROR-TEST"})
                
                # Check that error was logged
                mock_logger.error.assert_called_once()
                assert "Error generating prompt: Test error" in mock_logger.error.call_args[0][0]
        
        await builder.cleanup()


class TestPromptBuilderTemplates:
    """Test individual template generation methods."""
    
    def test_feature_template_with_lists(self):
        """Test feature template with list data."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "FEAT-LIST",
            "summary": "Feature with lists",
            "description": "Testing list handling",
            "acceptance_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
            "files_affected": ["file1.py", "file2.py", "file3.py"],
            "labels": ["feature", "backend", "urgent"],
            "components": ["auth", "api", "database"]
        }
        
        prompt = builder._generate_feature_prompt(ticket_data)
        
        # Check list formatting
        assert "- Criterion 1" in prompt
        assert "- Criterion 2" in prompt
        assert "- Criterion 3" in prompt
        assert "- file1.py" in prompt
        assert "- file2.py" in prompt
        assert "- file3.py" in prompt
        assert "feature, backend, urgent" in prompt
        assert "auth, api, database" in prompt
    
    def test_feature_template_with_strings(self):
        """Test feature template with string data."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "FEAT-STR",
            "summary": "Feature with strings",
            "description": "Testing string handling",
            "acceptance_criteria": "Single acceptance criterion",
            "files_affected": "single_file.py",
            "labels": "single_label",
            "components": "single_component"
        }
        
        prompt = builder._generate_feature_prompt(ticket_data)
        
        # Check string formatting
        assert "- Single acceptance criterion" in prompt
        assert "- single_file.py" in prompt
        assert "single_label" in prompt
        assert "single_component" in prompt
    
    def test_bugfix_template_minimal(self):
        """Test bugfix template with minimal data."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "BUG-MIN",
            "summary": "Minimal bug",
            "description": "Basic bug description"
        }
        
        prompt = builder._generate_bugfix_prompt(ticket_data)
        
        assert "BUG-MIN" in prompt
        assert "Minimal bug" in prompt
        assert "Basic bug description" in prompt
        assert "Medium" in prompt  # default priority
        assert "unknown" in prompt  # default feature
        assert "unassigned" in prompt  # default assignee
    
    def test_refactor_template_minimal(self):
        """Test refactor template with minimal data."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "REF-MIN",
            "summary": "Minimal refactor",
            "description": "Basic refactor description"
        }
        
        prompt = builder._generate_refactor_prompt(ticket_data)
        
        assert "REF-MIN" in prompt
        assert "Minimal refactor" in prompt
        assert "Basic refactor description" in prompt
        assert "Medium" in prompt  # default priority
        assert "unknown" in prompt  # default feature
        assert "unassigned" in prompt  # default assignee
    
    def test_enrichment_data_handling(self):
        """Test enrichment data handling in feature template."""
        builder = PromptBuilder()
        
        ticket_data = {
            "ticket_id": "ENRICH-TEST",
            "summary": "Enrichment test",
            "description": "Testing enrichment",
            "acceptance_criteria": ["Test enrichment"],
            "files_affected": ["enrich.py"]
        }
        
        # Test with enrichment data
        enrichment_data = {
            "context_enriched": True,
            "complexity_score": 7.2,
            "related_files": ["related1.py", "related2.py"],
            "related_tickets": ["TICKET-1", "TICKET-2"]
        }
        
        prompt = builder._generate_feature_prompt(ticket_data, enrichment_data)
        
        assert "## 🧠 Context & Insights" in prompt
        assert "7.2" in prompt
        assert "related1.py, related2.py" in prompt
        assert "TICKET-1, TICKET-2" in prompt
        
        # Test without enrichment data
        prompt_no_enrich = builder._generate_feature_prompt(ticket_data)
        assert "## 🧠 Context & Insights" not in prompt_no_enrich
        
        # Test with empty enrichment data
        empty_enrichment = {"context_enriched": False}
        prompt_empty = builder._generate_feature_prompt(ticket_data, empty_enrichment)
        assert "## 🧠 Context & Insights" not in prompt_empty 