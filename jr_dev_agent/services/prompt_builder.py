"""
Prompt Builder Service

This service is responsible for generating AI-optimized prompts from ticket data
and templates. It acts as a bridge between the LangGraph workflow and the
template engine.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime


class PromptBuilder:
    """
    Prompt Builder Service
    
    Generates AI-optimized prompts for GitHub Copilot based on ticket data
    and selected templates.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.initialized = False
    
    async def initialize(self):
        """Initialize the prompt builder"""
        self.logger.info("Initializing PromptBuilder...")
        self.initialized = True
        self.logger.info("PromptBuilder initialized successfully")
    
    async def generate_prompt(self, template_name: str, ticket_data: Dict[str, Any], 
                            enrichment_data: Dict[str, Any] = None) -> str:
        """
        Generate an AI-optimized prompt
        
        Args:
            template_name: Name of the template to use
            ticket_data: Ticket metadata
            enrichment_data: Optional enrichment data from Synthetic Memory
            
        Returns:
            Generated prompt string
        """
        try:
            self.logger.info(f"Generating prompt for ticket {ticket_data['ticket_id']} using template {template_name}")
            
            # Generate the prompt based on template
            if ticket_data.get('prompt_text'):
                self.logger.info(f"Using provided prompt_text from ticket data")
                prompt = ticket_data['prompt_text']
            elif template_name == "feature":
                prompt = self._generate_feature_prompt(ticket_data, enrichment_data)
            elif template_name == "bugfix":
                prompt = self._generate_bugfix_prompt(ticket_data, enrichment_data)
            elif template_name == "refactor":
                prompt = self._generate_refactor_prompt(ticket_data, enrichment_data)
            elif template_name == "feature_schema_change":
                prompt = self._generate_feature_prompt(ticket_data, enrichment_data)
            elif template_name in ["schema_change", "version_upgrade", "config_update"]:
                # Use feature template for maintenance/config tasks for now
                prompt = self._generate_feature_prompt(ticket_data, enrichment_data)
            elif template_name == "test_generation":
                # Use feature template structure for test generation
                prompt = self._generate_feature_prompt(ticket_data, enrichment_data)
            else:
                # Fallback to feature template
                self.logger.warning(f"Unknown template {template_name}, using feature template")
                prompt = self._generate_feature_prompt(ticket_data, enrichment_data)
            
            self.logger.info(f"Successfully generated prompt for {ticket_data['ticket_id']} (length: {len(prompt)})")
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error generating prompt: {str(e)}")
            raise
    
    def _generate_feature_prompt(self, ticket_data: Dict[str, Any], 
                               enrichment_data: Dict[str, Any] = None) -> str:
        """Generate prompt for feature implementation"""
        
        acceptance_criteria = ticket_data.get('acceptance_criteria', [])
        if isinstance(acceptance_criteria, list):
            criteria_text = '\n'.join([f"- {criteria}" for criteria in acceptance_criteria])
        else:
            criteria_text = f"- {acceptance_criteria}"
        
        files_affected = ticket_data.get('files_affected', [])
        if isinstance(files_affected, list):
            files_text = '\n'.join([f"- {file}" for file in files_affected])
        else:
            files_text = f"- {files_affected}"
        
        labels = ticket_data.get('labels', [])
        if isinstance(labels, list):
            labels_text = ', '.join(labels)
        else:
            labels_text = str(labels)
        
        components = ticket_data.get('components', [])
        if isinstance(components, list):
            components_text = ', '.join(components)
        else:
            components_text = str(components)
        
        # Add enrichment context if available
        enrichment_section = ""
        if enrichment_data and enrichment_data.get('context_enriched'):
            enrichment_section = f"""
## 🧠 Context & Insights
- **Complexity Score**: {enrichment_data.get('complexity_score', 'N/A')}
- **Related Files**: {', '.join(enrichment_data.get('related_files', [])) or 'None identified'}
- **Related Tickets**: {', '.join(enrichment_data.get('related_tickets', [])) or 'None identified'}
"""
        
        prompt = f"""# 🎯 Development Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Feature**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Description
{ticket_data['description']}

## ✅ Acceptance Criteria
{criteria_text}

## 📁 Files to Modify
{files_text}

## 🏷️ Labels & Components
- **Labels**: {labels_text}
- **Components**: {components_text}
{enrichment_section}
## 🤖 Instructions for GitHub Copilot
1. Review the ticket requirements above
2. Implement the necessary changes in the specified files
3. Follow best practices for code quality and testing
4. Ensure all acceptance criteria are met
5. Create or update tests as needed

## 🔧 Technical Guidelines
- Use TypeScript for type safety
- Follow existing code patterns and conventions
- Add proper error handling
- Include comprehensive comments
- Write unit tests for new functionality

## 📋 Implementation Checklist
- [ ] Understand the requirements thoroughly
- [ ] Plan the implementation approach
- [ ] Implement the core functionality
- [ ] Add proper error handling
- [ ] Write comprehensive tests
- [ ] Update documentation if needed
- [ ] Verify all acceptance criteria are met

**Note**: This prompt was generated using the '{ticket_data.get('template_name', 'feature')}' template. Data source: {ticket_data.get('source', 'mcp')}.
"""
        
        return prompt.strip()
    
    def _generate_bugfix_prompt(self, ticket_data: Dict[str, Any], 
                              enrichment_data: Dict[str, Any] = None) -> str:
        """Generate prompt for bug fix implementation"""
        
        acceptance_criteria = ticket_data.get('acceptance_criteria', [])
        if isinstance(acceptance_criteria, list):
            criteria_text = '\n'.join([f"- {criteria}" for criteria in acceptance_criteria])
        else:
            criteria_text = f"- {acceptance_criteria}"
        
        files_affected = ticket_data.get('files_affected', [])
        if isinstance(files_affected, list):
            files_text = '\n'.join([f"- {file}" for file in files_affected])
        else:
            files_text = f"- {files_affected}"
        
        prompt = f"""# 🐛 Bug Fix Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Bug Component**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Bug Description
{ticket_data['description']}

## ✅ Fix Criteria
{criteria_text}

## 📁 Files to Investigate/Fix
{files_text}

## 🤖 Instructions for GitHub Copilot
1. **Analyze the bug**: Understand the root cause of the issue
2. **Identify the fix**: Determine the minimal change needed
3. **Implement the solution**: Make targeted changes to fix the bug
4. **Add regression tests**: Ensure the bug doesn't happen again
5. **Verify the fix**: Test that the issue is resolved

## 🔧 Bug Fix Guidelines
- Make minimal, targeted changes
- Avoid over-engineering the solution
- Add tests to prevent regression
- Document the fix in code comments
- Consider edge cases and error handling

## 📋 Bug Fix Checklist
- [ ] Reproduce the bug locally
- [ ] Identify the root cause
- [ ] Implement the minimal fix
- [ ] Add regression tests
- [ ] Verify the fix works
- [ ] Test for unintended side effects

**Note**: This is a bug fix prompt generated from ticket {ticket_data['ticket_id']}. Focus on targeted fixes rather than major refactoring.
"""
        
        return prompt.strip()
    
    def _generate_refactor_prompt(self, ticket_data: Dict[str, Any], 
                                enrichment_data: Dict[str, Any] = None) -> str:
        """Generate prompt for refactoring implementation"""
        
        acceptance_criteria = ticket_data.get('acceptance_criteria', [])
        if isinstance(acceptance_criteria, list):
            criteria_text = '\n'.join([f"- {criteria}" for criteria in acceptance_criteria])
        else:
            criteria_text = f"- {acceptance_criteria}"
        
        files_affected = ticket_data.get('files_affected', [])
        if isinstance(files_affected, list):
            files_text = '\n'.join([f"- {file}" for file in files_affected])
        else:
            files_text = f"- {files_affected}"
        
        prompt = f"""# 🔄 Refactoring Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Component**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Refactoring Description
{ticket_data['description']}

## ✅ Refactoring Goals
{criteria_text}

## 📁 Files to Refactor
{files_text}

## 🤖 Instructions for GitHub Copilot
1. **Analyze existing code**: Understand current implementation
2. **Identify improvements**: Find areas for better structure/performance
3. **Plan the refactoring**: Design the improved architecture
4. **Implement incrementally**: Make step-by-step improvements
5. **Maintain functionality**: Ensure behavior remains the same
6. **Update tests**: Modify tests as needed for new structure

## 🔧 Refactoring Guidelines
- Maintain existing functionality
- Improve code readability and maintainability
- Follow SOLID principles
- Reduce code duplication
- Improve performance where possible
- Update documentation and comments

## 📋 Refactoring Checklist
- [ ] Understand current code structure
- [ ] Identify refactoring opportunities
- [ ] Plan the refactoring approach
- [ ] Implement changes incrementally
- [ ] Run tests frequently
- [ ] Update documentation
- [ ] Verify no functionality regression

**Note**: This is a refactoring prompt. Focus on improving code quality while maintaining existing functionality.
"""
        
        return prompt.strip()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the prompt builder"""
        return {
            "initialized": self.initialized,
            "service": "PromptBuilder",
            "version": "1.0.0",
            "supported_templates": [
                "feature", "bugfix", "refactor", "feature_schema_change",
                "schema_change", "version_upgrade", "config_update", "test_generation"
            ]
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("PromptBuilder cleanup complete")
        self.initialized = False 