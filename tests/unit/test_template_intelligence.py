"""
Unit tests for Template Intelligence service core functionality.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../template_intelligence'))

from template_intelligence.engine.template_engine import TemplateEngine, template_engine


class TestTemplateEngineCore:
    """Test TemplateEngine core functionality."""
    
    def test_template_engine_initialization(self):
        """Test TemplateEngine initialization."""
        engine = TemplateEngine()
        assert engine is not None
        assert not engine.initialized
        assert hasattr(engine, 'logger')
        assert hasattr(engine, 'templates')
        assert len(engine.templates) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_method(self):
        """Test service initialization."""
        engine = TemplateEngine()
        await engine.initialize()
        
        assert engine.initialized
        assert len(engine.templates) > 0
        
        # Check that default templates are loaded
        expected_templates = [
            "feature", "bugfix", "refactor", "version_upgrade", 
            "config_update", "schema_change", "test_generation"
        ]
        for template_name in expected_templates:
            assert template_name in engine.templates
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test service cleanup."""
        engine = TemplateEngine()
        await engine.initialize()
        assert engine.initialized
        
        await engine.cleanup()
        assert not engine.initialized
    
    def test_get_status(self):
        """Test status reporting."""
        engine = TemplateEngine()
        status = engine.get_status()
        
        assert isinstance(status, dict)
        assert "initialized" in status
        assert "service" in status
        assert "version" in status
        assert "total_templates" in status
        assert "template_names" in status
        assert "categories" in status
        
        assert status["service"] == "TemplateEngine"
        assert status["version"] == "1.0.0"
        assert status["total_templates"] == 0  # Not initialized yet
        assert status["template_names"] == []
    
    @pytest.mark.asyncio
    async def test_load_default_templates(self):
        """Test loading of default templates."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Check feature template
        feature_template = engine.get_template("feature")
        assert feature_template is not None
        assert feature_template["name"] == "feature"
        assert feature_template["category"] == "development"
        assert "implement" in feature_template["keywords"]
        assert feature_template["priority"] == 1
        
        # Check bugfix template
        bugfix_template = engine.get_template("bugfix")
        assert bugfix_template is not None
        assert bugfix_template["name"] == "bugfix"
        assert bugfix_template["category"] == "maintenance"
        assert "bug" in bugfix_template["keywords"]
        assert bugfix_template["priority"] == 2
        
        # Check refactor template
        refactor_template = engine.get_template("refactor")
        assert refactor_template is not None
        assert refactor_template["name"] == "refactor"
        assert refactor_template["category"] == "maintenance"
        assert "refactor" in refactor_template["keywords"]
        assert refactor_template["priority"] == 3
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_has_template(self):
        """Test template existence check."""
        engine = TemplateEngine()
        await engine.initialize()
        
        assert engine.has_template("feature")
        assert engine.has_template("bugfix")
        assert engine.has_template("refactor")
        assert not engine.has_template("nonexistent")
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_template(self):
        """Test getting specific template."""
        engine = TemplateEngine()
        await engine.initialize()
        
        feature_template = engine.get_template("feature")
        assert feature_template is not None
        assert isinstance(feature_template, dict)
        assert feature_template["name"] == "feature"
        
        nonexistent_template = engine.get_template("nonexistent")
        assert nonexistent_template is None
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_all_templates(self):
        """Test getting all templates."""
        engine = TemplateEngine()
        await engine.initialize()
        
        all_templates = engine.get_all_templates()
        assert isinstance(all_templates, dict)
        assert len(all_templates) == 7  # 7 default templates
        
        expected_templates = [
            "feature", "bugfix", "refactor", "version_upgrade", 
            "config_update", "schema_change", "test_generation"
        ]
        for template_name in expected_templates:
            assert template_name in all_templates
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_select_template_explicit(self):
        """Test template selection with explicit template name."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test explicit valid template
        ticket_data = {
            "ticket_id": "EXPLICIT-123",
            "template_name": "bugfix",
            "summary": "Fix login issue",
            "description": "Users cannot login"
        }
        
        selected = engine.select_template(ticket_data)
        assert selected == "bugfix"
        
        # Test explicit invalid template (should fallback to auto-selection)
        ticket_data["template_name"] = "nonexistent"
        selected = engine.select_template(ticket_data)
        assert selected in ["feature", "bugfix", "refactor"]  # Should auto-select
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_select_template_auto_selection(self):
        """Test automatic template selection based on content."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test bug-related ticket
        bug_ticket = {
            "ticket_id": "BUG-123",
            "summary": "Fix login bug",
            "description": "Users are experiencing login issues and errors",
            "labels": ["bug", "critical"]
        }
        
        selected = engine.select_template(bug_ticket)
        assert selected == "bugfix"
        
        # Test feature-related ticket
        feature_ticket = {
            "ticket_id": "FEAT-456",
            "summary": "Add new feature",
            "description": "Implement new user authentication feature",
            "labels": ["feature", "enhancement"]
        }
        
        selected = engine.select_template(feature_ticket)
        assert selected == "feature"
        
        # Test refactor-related ticket
        refactor_ticket = {
            "ticket_id": "REF-789",
            "summary": "Refactor authentication module",
            "description": "Improve and optimize the authentication code",
            "labels": ["refactor", "improvement"]
        }
        
        selected = engine.select_template(refactor_ticket)
        assert selected == "refactor"
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_content(self):
        """Test ticket content analysis."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test with bug keywords
        bug_ticket = {
            "summary": "Fix critical bug in login system",
            "description": "There's a serious bug causing login failures",
            "labels": ["bug", "critical", "fix"]
        }
        
        selected = engine._analyze_ticket_content(bug_ticket)
        assert selected == "bugfix"
        
        # Test with feature keywords
        feature_ticket = {
            "summary": "Add new authentication feature",
            "description": "Implement OAuth2 authentication feature",
            "labels": ["feature", "new", "enhancement"]
        }
        
        selected = engine._analyze_ticket_content(feature_ticket)
        assert selected == "feature"
        
        # Test with refactor keywords
        refactor_ticket = {
            "summary": "Refactor user service",
            "description": "Cleanup and optimize user service code",
            "labels": ["refactor", "cleanup", "optimize"]
        }
        
        selected = engine._analyze_ticket_content(refactor_ticket)
        assert selected == "refactor"
        
        # Test with version upgrade keywords
        upgrade_ticket = {
            "summary": "Upgrade React version",
            "description": "Update React dependency to latest version",
            "labels": ["upgrade", "dependency", "update"]
        }
        
        selected = engine._analyze_ticket_content(upgrade_ticket)
        assert selected == "version_upgrade"
        
        # Test with no matching keywords (should default to feature)
        empty_ticket = {
            "summary": "Random task",
            "description": "Some random task description",
            "labels": []
        }
        
        selected = engine._analyze_ticket_content(empty_ticket)
        assert selected == "feature"
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_template_suggestions(self):
        """Test template suggestions."""
        engine = TemplateEngine()
        await engine.initialize()
        
        ticket_data = {
            "summary": "Fix bug and refactor code",
            "description": "Fix the login bug and also refactor the authentication module",
            "labels": ["bug", "refactor", "fix"]
        }
        
        suggestions = engine.get_template_suggestions(ticket_data)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5  # Default limit
        
        # Check suggestion structure
        if suggestions:
            suggestion = suggestions[0]
            assert "template_name" in suggestion
            assert "score" in suggestion
            assert "description" in suggestion
            assert "category" in suggestion
            assert "matched_keywords" in suggestion
            
            # Should be sorted by score (highest first)
            assert suggestion["score"] >= 0
            
        # Test with limit
        limited_suggestions = engine.get_template_suggestions(ticket_data, limit=3)
        assert len(limited_suggestions) <= 3
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_validate_template_data(self):
        """Test template data validation."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test with valid data
        valid_ticket_data = {
            "ticket_id": "VALID-123",
            "summary": "Valid ticket",
            "description": "Valid description",
            "acceptance_criteria": ["Criterion 1"],
            "files_affected": ["file1.py"]
        }
        
        result = engine.validate_template_data("feature", valid_ticket_data)
        assert result["valid"] is True
        assert len(result["missing_fields"]) == 0
        assert "template_info" in result
        
        # Test with missing required fields
        invalid_ticket_data = {
            "ticket_id": "INVALID-123"
            # Missing summary and description
        }
        
        result = engine.validate_template_data("feature", invalid_ticket_data)
        assert result["valid"] is False
        assert "summary" in result["missing_fields"]
        assert "description" in result["missing_fields"]
        
        # Test with nonexistent template
        result = engine.validate_template_data("nonexistent", valid_ticket_data)
        assert result["valid"] is False
        assert "Template nonexistent not found" in result["error"]
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_template_categories(self):
        """Test getting template categories."""
        engine = TemplateEngine()
        await engine.initialize()
        
        categories = engine.get_template_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        expected_categories = ["configuration", "data", "development", "maintenance", "testing"]
        for category in expected_categories:
            assert category in categories
        
        # Categories should be sorted
        assert categories == sorted(categories)
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_templates_by_category(self):
        """Test getting templates by category."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test development category
        dev_templates = engine.get_templates_by_category("development")
        assert isinstance(dev_templates, list)
        assert len(dev_templates) > 0
        
        # All templates should be in development category
        for template in dev_templates:
            assert template["category"] == "development"
        
        # Test maintenance category
        maintenance_templates = engine.get_templates_by_category("maintenance")
        assert isinstance(maintenance_templates, list)
        assert len(maintenance_templates) > 0
        
        # All templates should be in maintenance category
        for template in maintenance_templates:
            assert template["category"] == "maintenance"
        
        # Test nonexistent category
        nonexistent_templates = engine.get_templates_by_category("nonexistent")
        assert isinstance(nonexistent_templates, list)
        assert len(nonexistent_templates) == 0
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in template selection."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test with None ticket data
        with patch.object(engine, 'logger') as mock_logger:
            selected = engine.select_template(None)
            assert selected == "feature"  # Fallback
            mock_logger.error.assert_called_once()
        
        # Test with invalid ticket data structure
        with patch.object(engine, 'logger') as mock_logger:
            selected = engine.select_template("invalid")
            assert selected == "feature"  # Fallback
            mock_logger.error.assert_called_once()
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_template_priority_scoring(self):
        """Test template priority scoring in selection."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test ticket with multiple matching keywords
        mixed_ticket = {
            "summary": "Fix bug and add new feature",
            "description": "Fix the existing bug and implement new feature",
            "labels": ["bug", "fix", "feature", "new"]
        }
        
        # Should prefer higher priority template (bug = priority 2, feature = priority 1)
        # But feature has higher priority (lower number), so it should win if scores are equal
        selected = engine.select_template(mixed_ticket)
        assert selected in ["feature", "bugfix"]  # Either could win based on exact scoring
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_template_keyword_matching(self):
        """Test keyword matching in template selection."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Test exact keyword match
        exact_match_ticket = {
            "summary": "schema migration needed",
            "description": "We need to create a database schema migration",
            "labels": ["schema", "database", "migration"]
        }
        
        selected = engine.select_template(exact_match_ticket)
        assert selected == "schema_change"
        
        # Test partial keyword match
        partial_match_ticket = {
            "summary": "test coverage improvement",
            "description": "We need to improve test coverage",
            "labels": ["test", "testing", "coverage"]
        }
        
        selected = engine.select_template(partial_match_ticket)
        assert selected == "test_generation"
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_template_suggestions_scoring(self):
        """Test template suggestions scoring."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Create ticket with clear bug keywords
        bug_ticket = {
            "summary": "Critical bug fix needed",
            "description": "Fix the critical bug in login system",
            "labels": ["bug", "critical", "fix", "issue"]
        }
        
        suggestions = engine.get_template_suggestions(bug_ticket)
        
        # Bugfix template should have highest score
        assert suggestions[0]["template_name"] == "bugfix"
        assert suggestions[0]["score"] > 0
        
        # Check that matched keywords are tracked
        assert len(suggestions[0]["matched_keywords"]) > 0
        assert "bug" in suggestions[0]["matched_keywords"]
        assert "fix" in suggestions[0]["matched_keywords"]
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_template_operations(self):
        """Test concurrent template operations."""
        engine = TemplateEngine()
        await engine.initialize()
        
        # Create multiple concurrent requests
        tickets = [
            {"summary": f"Fix bug {i}", "description": f"Bug fix {i}", "labels": ["bug"]},
            {"summary": f"Add feature {i}", "description": f"New feature {i}", "labels": ["feature"]},
            {"summary": f"Refactor code {i}", "description": f"Code refactor {i}", "labels": ["refactor"]}
        ]
        
        # Execute template selections concurrently
        tasks = [engine.select_template(ticket) for ticket in tickets]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == len(tickets)
        for result in results:
            assert result in ["feature", "bugfix", "refactor"]
        
        await engine.cleanup()
    
    def test_global_template_engine_instance(self):
        """Test that global template_engine instance exists."""
        assert template_engine is not None
        assert isinstance(template_engine, TemplateEngine)


class TestTemplateEngineTemplates:
    """Test individual template configurations."""
    
    @pytest.mark.asyncio
    async def test_feature_template_config(self):
        """Test feature template configuration."""
        engine = TemplateEngine()
        await engine.initialize()
        
        template = engine.get_template("feature")
        assert template["name"] == "feature"
        assert template["category"] == "development"
        assert template["priority"] == 1
        
        # Check required fields
        required_fields = template["required_fields"]
        assert "ticket_id" in required_fields
        assert "summary" in required_fields
        assert "description" in required_fields
        
        # Check keywords
        keywords = template["keywords"]
        assert "feature" in keywords
        assert "enhancement" in keywords
        assert "new" in keywords
        assert "implement" in keywords
        assert "add" in keywords
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_bugfix_template_config(self):
        """Test bugfix template configuration."""
        engine = TemplateEngine()
        await engine.initialize()
        
        template = engine.get_template("bugfix")
        assert template["name"] == "bugfix"
        assert template["category"] == "maintenance"
        assert template["priority"] == 2
        
        # Check keywords
        keywords = template["keywords"]
        assert "bug" in keywords
        assert "fix" in keywords
        assert "issue" in keywords
        assert "problem" in keywords
        assert "error" in keywords
        assert "defect" in keywords
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_all_template_configs(self):
        """Test all template configurations."""
        engine = TemplateEngine()
        await engine.initialize()
        
        expected_templates = {
            "feature": {"category": "development", "priority": 1},
            "bugfix": {"category": "maintenance", "priority": 2},
            "refactor": {"category": "maintenance", "priority": 3},
            "version_upgrade": {"category": "maintenance", "priority": 4},
            "config_update": {"category": "configuration", "priority": 5},
            "schema_change": {"category": "data", "priority": 6},
            "test_generation": {"category": "testing", "priority": 7}
        }
        
        for template_name, expected_config in expected_templates.items():
            template = engine.get_template(template_name)
            assert template is not None
            assert template["name"] == template_name
            assert template["category"] == expected_config["category"]
            assert template["priority"] == expected_config["priority"]
            
            # All templates should have required fields
            assert "required_fields" in template
            assert "optional_fields" in template
            assert "keywords" in template
            assert "description" in template
            assert "version" in template
            
            # Check that basic required fields are present
            required_fields = template["required_fields"]
            assert "ticket_id" in required_fields
            assert "summary" in required_fields
            assert "description" in required_fields
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_template_keyword_uniqueness(self):
        """Test that template keywords are appropriate and somewhat unique."""
        engine = TemplateEngine()
        await engine.initialize()
        
        all_templates = engine.get_all_templates()
        
        # Collect all keywords
        all_keywords = {}
        for template_name, template in all_templates.items():
            keywords = template["keywords"]
            for keyword in keywords:
                if keyword not in all_keywords:
                    all_keywords[keyword] = []
                all_keywords[keyword].append(template_name)
        
        # Check that some keywords are unique to specific templates
        # (This helps ensure good template selection)
        assert len(all_keywords["bug"]) == 1
        assert all_keywords["bug"][0] == "bugfix"
        
        assert len(all_keywords["refactor"]) == 1
        assert all_keywords["refactor"][0] == "refactor"
        
        assert len(all_keywords["schema"]) == 1
        assert all_keywords["schema"][0] == "schema_change"
        
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_template_validation_fields(self):
        """Test template validation fields."""
        engine = TemplateEngine()
        await engine.initialize()
        
        all_templates = engine.get_all_templates()
        
        for template_name, template in all_templates.items():
            # Test validation with minimal required fields
            minimal_ticket = {
                "ticket_id": f"TEST-{template_name}",
                "summary": f"Test {template_name}",
                "description": f"Test description for {template_name}"
            }
            
            result = engine.validate_template_data(template_name, minimal_ticket)
            assert result["valid"] is True
            assert len(result["missing_fields"]) == 0
            
            # Test validation with missing required field
            incomplete_ticket = {
                "ticket_id": f"TEST-{template_name}",
                "summary": f"Test {template_name}"
                # Missing description
            }
            
            result = engine.validate_template_data(template_name, incomplete_ticket)
            assert result["valid"] is False
            assert "description" in result["missing_fields"]
        
        await engine.cleanup() 