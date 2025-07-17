"""
Template Engine Service

This service manages prompt templates and provides template selection logic
for the Jr Dev Agent system.
"""

import logging
from typing import Dict, Any, List, Optional, Set


class TemplateEngine:
    """
    Template Engine Service
    
    Manages prompt templates and provides template selection logic
    for different types of development tasks.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize the template engine with default templates"""
        self.logger.info("Initializing TemplateEngine...")
        
        # Load default templates
        self._load_default_templates()
        
        self.initialized = True
        self.logger.info(f"TemplateEngine initialized with {len(self.templates)} templates")
    
    def _load_default_templates(self):
        """Load default template configurations"""
        
        # Feature template
        self.templates["feature"] = {
            "name": "feature",
            "version": "1.0",
            "description": "Template for new feature implementation",
            "category": "development",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["feature", "enhancement", "new", "implement", "add"],
            "priority": 1
        }
        
        # Bug fix template
        self.templates["bugfix"] = {
            "name": "bugfix",
            "version": "1.0", 
            "description": "Template for bug fix implementation",
            "category": "maintenance",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["bug", "fix", "issue", "problem", "error", "defect"],
            "priority": 2
        }
        
        # Refactor template
        self.templates["refactor"] = {
            "name": "refactor",
            "version": "1.0",
            "description": "Template for code refactoring",
            "category": "maintenance",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["refactor", "cleanup", "improve", "optimize", "restructure"],
            "priority": 3
        }
        
        # Version upgrade template
        self.templates["version_upgrade"] = {
            "name": "version_upgrade",
            "version": "1.0",
            "description": "Template for dependency version upgrades",
            "category": "maintenance",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["upgrade", "update", "version", "dependency", "package"],
            "priority": 4
        }
        
        # Configuration update template
        self.templates["config_update"] = {
            "name": "config_update",
            "version": "1.0",
            "description": "Template for configuration changes",
            "category": "configuration",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["config", "configuration", "settings", "environment", "deploy"],
            "priority": 5
        }
        
        # Schema change template
        self.templates["schema_change"] = {
            "name": "schema_change",
            "version": "1.0",
            "description": "Template for database or GraphQL schema changes",
            "category": "data",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["schema", "database", "graphql", "migration", "table"],
            "priority": 6
        }
        
        # Test generation template
        self.templates["test_generation"] = {
            "name": "test_generation",
            "version": "1.0",
            "description": "Template for test case creation",
            "category": "testing",
            "required_fields": ["ticket_id", "summary", "description"],
            "optional_fields": ["acceptance_criteria", "files_affected", "labels", "components"],
            "keywords": ["test", "testing", "unit", "integration", "coverage"],
            "priority": 7
        }
    
    def has_template(self, template_name: str) -> bool:
        """
        Check if a template exists
        
        Args:
            template_name: Name of the template to check
            
        Returns:
            True if template exists, False otherwise
        """
        return template_name in self.templates
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by name
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template configuration or None if not found
        """
        return self.templates.get(template_name)
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available templates
        
        Returns:
            Dictionary of all templates
        """
        return self.templates.copy()
    
    def select_template(self, ticket_data: Dict[str, Any]) -> str:
        """
        Select the best template for a given ticket
        
        Args:
            ticket_data: Ticket metadata
            
        Returns:
            Selected template name
        """
        try:
            # Check if template is explicitly specified
            if 'template_name' in ticket_data and ticket_data['template_name']:
                template_name = ticket_data['template_name']
                if self.has_template(template_name):
                    self.logger.info(f"Using explicitly specified template: {template_name}")
                    return template_name
                else:
                    self.logger.warning(f"Specified template {template_name} not found, using auto-selection")
            
            # Auto-select based on content analysis
            selected_template = self._analyze_ticket_content(ticket_data)
            
            self.logger.info(f"Auto-selected template: {selected_template} for ticket {ticket_data.get('ticket_id', 'unknown')}")
            return selected_template
            
        except Exception as e:
            self.logger.error(f"Error selecting template: {str(e)}")
            return "feature"  # Fallback to feature template
    
    def _analyze_ticket_content(self, ticket_data: Dict[str, Any]) -> str:
        """
        Analyze ticket content to determine the best template
        
        Args:
            ticket_data: Ticket metadata
            
        Returns:
            Selected template name
        """
        # Combine text fields for analysis
        text_content = []
        
        if 'summary' in ticket_data:
            text_content.append(ticket_data['summary'].lower())
        
        if 'description' in ticket_data:
            text_content.append(ticket_data['description'].lower())
        
        if 'labels' in ticket_data:
            labels = ticket_data['labels']
            if isinstance(labels, list):
                text_content.extend([label.lower() for label in labels])
            else:
                text_content.append(str(labels).lower())
        
        combined_text = ' '.join(text_content)
        
        # Score each template based on keyword matches
        template_scores = {}
        
        for template_name, template_config in self.templates.items():
            score = 0
            keywords = template_config.get('keywords', [])
            
            # Count keyword matches
            for keyword in keywords:
                keyword_count = combined_text.count(keyword.lower())
                score += keyword_count
            
            # Apply priority weight (lower priority number = higher weight)
            priority = template_config.get('priority', 10)
            score = score * (11 - priority)  # Invert priority so lower number = higher weight
            
            template_scores[template_name] = score
        
        # Select template with highest score
        if template_scores:
            best_template = max(template_scores.items(), key=lambda x: x[1])
            
            # If no keywords matched, default to feature
            if best_template[1] == 0:
                return "feature"
            
            return best_template[0]
        
        return "feature"  # Default fallback
    
    def get_template_suggestions(self, ticket_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get template suggestions for a ticket
        
        Args:
            ticket_data: Ticket metadata
            limit: Maximum number of suggestions
            
        Returns:
            List of template suggestions with scores
        """
        try:
            # Combine text fields for analysis
            text_content = []
            
            if 'summary' in ticket_data:
                text_content.append(ticket_data['summary'].lower())
            
            if 'description' in ticket_data:
                text_content.append(ticket_data['description'].lower())
            
            if 'labels' in ticket_data:
                labels = ticket_data['labels']
                if isinstance(labels, list):
                    text_content.extend([label.lower() for label in labels])
                else:
                    text_content.append(str(labels).lower())
            
            combined_text = ' '.join(text_content)
            
            # Score all templates
            suggestions = []
            
            for template_name, template_config in self.templates.items():
                score = 0
                keywords = template_config.get('keywords', [])
                
                # Count keyword matches
                for keyword in keywords:
                    keyword_count = combined_text.count(keyword.lower())
                    score += keyword_count
                
                # Apply priority weight
                priority = template_config.get('priority', 10)
                score = score * (11 - priority)
                
                suggestions.append({
                    'template_name': template_name,
                    'score': score,
                    'description': template_config.get('description', ''),
                    'category': template_config.get('category', 'unknown'),
                    'matched_keywords': [kw for kw in keywords if kw.lower() in combined_text]
                })
            
            # Sort by score and return top suggestions
            suggestions.sort(key=lambda x: x['score'], reverse=True)
            return suggestions[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting template suggestions: {str(e)}")
            return []
    
    def validate_template_data(self, template_name: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that ticket data has required fields for a template
        
        Args:
            template_name: Template to validate against
            ticket_data: Ticket metadata
            
        Returns:
            Validation result with status and missing fields
        """
        template = self.get_template(template_name)
        
        if not template:
            return {
                'valid': False,
                'error': f'Template {template_name} not found',
                'missing_fields': [],
                'optional_fields': []
            }
        
        required_fields = template.get('required_fields', [])
        optional_fields = template.get('optional_fields', [])
        
        missing_fields = []
        
        for field in required_fields:
            if field not in ticket_data or not ticket_data[field]:
                missing_fields.append(field)
        
        return {
            'valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'optional_fields': optional_fields,
            'template_info': template
        }
    
    def get_template_categories(self) -> List[str]:
        """
        Get all template categories
        
        Returns:
            List of unique template categories
        """
        categories = set()
        for template in self.templates.values():
            categories.add(template.get('category', 'unknown'))
        return sorted(list(categories))
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get templates by category
        
        Args:
            category: Template category to filter by
            
        Returns:
            List of templates in the category
        """
        return [
            template for template in self.templates.values()
            if template.get('category') == category
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the template engine"""
        return {
            "initialized": self.initialized,
            "service": "TemplateEngine",
            "version": "1.0.0",
            "total_templates": len(self.templates),
            "template_names": list(self.templates.keys()),
            "categories": self.get_template_categories()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("TemplateEngine cleanup complete")
        self.initialized = False 