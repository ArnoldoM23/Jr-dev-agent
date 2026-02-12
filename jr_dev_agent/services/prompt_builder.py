"""
Prompt Builder Service

This service is responsible for generating AI-optimized prompts from ticket data
and templates. It acts as a bridge between the LangGraph workflow and the
template engine.
"""

import logging
import os
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
            prompt_text = ticket_data.get('prompt_text')
            description_text = ticket_data.get('description') or ""

            # Heuristic: some templates embed a short `prompt_text` but keep key requirements
            # (schema updates, file refs, commands) in the broader description. In those cases,
            # prefer a structured prompt that includes the full description.
            use_prompt_text_only = bool(prompt_text)

            # For schema-change style tickets, prefer structured prompts over raw prompt_text.
            # In practice, schema templates often split requirements across description sections,
            # and `prompt_text` may not include critical field definitions.
            if template_name in {"feature_schema_change", "schema_change"}:
                use_prompt_text_only = False

            if prompt_text and description_text:
                pt = prompt_text.strip().lower()
                dt = description_text.strip().lower()
                looks_truncated = (
                    len(pt) < max(200, int(0.5 * len(dt)))
                    and any(k in dt for k in ["schema types", "reference files", "fields_required"])
                    and not any(k in pt for k in ["schema types", "reference files", "fields_required"])
                )
                # Extra schema-specific truncation checks (common when prompt_text was extracted from YAML)
                if not looks_truncated and any(k in dt for k in ["lineitems:", "terms type", "placeorderinput", "npm run generate"]):
                    if not any(k in pt for k in ["lineitems:", "terms type", "placeorderinput", "npm run generate"]):
                        looks_truncated = True
                if looks_truncated:
                    use_prompt_text_only = False

            if use_prompt_text_only:
                self.logger.info("Using provided prompt_text from ticket data")
                prompt = prompt_text
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
            labels_text = ', '.join([str(l) for l in labels])
        else:
            labels_text = str(labels)
        
        components = ticket_data.get('components', [])
        if isinstance(components, list):
            components_text = ', '.join([str(c) for c in components])
        else:
            components_text = str(components)
        
        # Add enrichment context if available
        enrichment_section = ""
        if enrichment_data and enrichment_data.get('context_enriched'):
            # Safely handle related_files and related_tickets
            related_files = enrichment_data.get('related_files', [])
            if isinstance(related_files, dict):
                related_files_text = ', '.join([str(k) for k in related_files.keys()])
            elif isinstance(related_files, list):
                related_files_text = ', '.join([str(f) for f in related_files])
            else:
                related_files_text = str(related_files)

            related_tickets = enrichment_data.get('related_tickets', [])
            if isinstance(related_tickets, list):
                related_tickets_text = ', '.join([str(t) for t in related_tickets])
            else:
                related_tickets_text = str(related_tickets)

            enrichment_section = f"""
## 🧠 Context & Insights
- **Complexity Score**: {enrichment_data.get('complexity_score', 'N/A')}
- **Related Files**: {related_files_text or 'None identified'}
- **Related Tickets**: {related_tickets_text or 'None identified'}
"""
        
        # Add any additional fields from ticket data
        additional_fields_section = self._get_additional_fields_text(ticket_data)
        
        prompt = f"""# 🎯 Development Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Feature**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Description
{ticket_data['description']}
{additional_fields_section}
## ✅ Acceptance Criteria
{criteria_text}

## 📁 Files to Modify
{files_text}

## 🏷️ Labels & Components
- **Labels**: {labels_text}
- **Components**: {components_text}
{enrichment_section}
## 🤖 Instructions for GitHub Copilot/Cursor coding agent
1. Review the ticket requirements above
2. **Create a todo list**: Plan the implementation steps, including tests, PR creation, and session finalization.
3. **Start implementing the changes immediately** (the user has already approved this task via the tool call).
4. Implement the necessary changes in the specified files
5. Follow best practices for code quality and testing
6. Ensure all acceptance criteria are met
7. Create or update tests as needed, run them, and ensure they pass
8. Create a pull request with a clear title referencing the ticket ID
9. **Generate session summaries** for future context:
   - `change_required`: A 1-2 sentence summary of what changes were originally required (read the ticket above)
   - `changes_made`: A 1-2 sentence summary of what you actually implemented
10. Run the `finalize_session` tool with both summaries to complete the session

## 🔧 Technical Guidelines
- Use TypeScript for type safety
- Follow existing code patterns and conventions
- Add proper error handling
- Include comprehensive comments
- Write unit tests for new functionality

## 📋 Implementation Checklist
- [ ] Understand the requirements thoroughly
- [ ] Plan the implementation approach and write a todo list for the implementation.
- [ ] Implement the core functionality
- [ ] Add proper error handling
- [ ] Write comprehensive tests and verify they pass
- [ ] Update documentation if needed
- [ ] Verify all acceptance criteria are met
- [ ] After implementation, and test pass create a pull request with a clear title referencing the ticket ID and a summary of the changes made.
- [ ] Generate `change_required` summary: what changes were needed (1-2 sentences from the ticket)
- [ ] Generate `changes_made` summary: what was actually implemented (1-2 sentences)
- [ ] Run the finalize_session tool with both summaries to finalize the session.

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
        
        # Add any additional fields from ticket data
        additional_fields_section = self._get_additional_fields_text(ticket_data)
        
        prompt = f"""# 🐛 Bug Fix Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Bug Component**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Bug Description
{ticket_data['description']}
{additional_fields_section}
## ✅ Fix Criteria
{criteria_text}

## 📁 Files to Investigate/Fix
{files_text}

## 🤖 Instructions for GitHub Copilot/Cursor coding agent
1. **Analyze the bug**: Understand the root cause of the issue
2. **Create a todo list**: Plan the fix, including reproduction, tests, PR, and finalization.
3. **Identify the fix**: Determine the minimal change needed
4. **Start implementing the changes immediately** (the user has already approved this task via the tool call).
5. **Implement the solution**: Make targeted changes to fix the bug
6. **Add regression tests**: Ensure the bug doesn't happen again
7. **Verify the fix**: Test that the issue is resolved and all tests pass
8. **Create Pull Request**: Create a PR with the fix
9. **Generate session summaries**:
   - `change_required`: 1-2 sentence summary of what bug needed fixing
   - `changes_made`: 1-2 sentence summary of the fix implemented
10. **Finalize**: Run the `finalize_session` tool with both summaries

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
        
        # Add any additional fields from ticket data
        additional_fields_section = self._get_additional_fields_text(ticket_data)
        
        prompt = f"""# 🔄 Refactoring Task: {ticket_data['summary']}

## 📋 Ticket Information
- **Ticket ID**: {ticket_data['ticket_id']}
- **Priority**: {ticket_data.get('priority', 'Medium')}
- **Component**: {ticket_data.get('feature', 'unknown')}
- **Assignee**: {ticket_data.get('assignee', 'unassigned')}

## 📝 Refactoring Description
{ticket_data['description']}
{additional_fields_section}
## ✅ Refactoring Goals
{criteria_text}

## 📁 Files to Refactor
{files_text}

## 🤖 Instructions for GitHub Copilot/Cursor coding agent
1. **Analyze existing code**: Understand current implementation
2. **Create a todo list**: Plan the refactoring steps, tests, PR, and finalization.
3. **Identify improvements**: Find areas for better structure/performance
4. **Plan the refactoring**: Design the improved architecture
5. **Start implementing the changes immediately** (the user has already approved this task via the tool call).
6. **Implement incrementally**: Make step-by-step improvements
7. **Maintain functionality**: Ensure behavior remains the same
8. **Update tests**: Modify tests as needed for new structure, run them, and ensure they pass
9. **Create Pull Request**: Create a PR with the changes
10. **Generate session summaries**:
    - `change_required`: 1-2 sentence summary of what needed refactoring
    - `changes_made`: 1-2 sentence summary of the refactoring done
11. **Finalize**: Run the `finalize_session` tool with both summaries

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

    def _get_additional_fields_text(self, ticket_data: Dict[str, Any]) -> str:
        """Extract and format any extra fields not covered by the main template"""
        additional_text = ""
        
        # Define fields we already handle explicitly
        standard_fields = {
            'ticket_id', 'summary', 'description', 'acceptance_criteria', 
            'files_affected', 'priority', 'feature', 'assignee', 'labels', 
            'components', 'template_name', 'source', 'prompt_text'
        }
        
        # Check for any extra fields
        extras = []
        for key, value in ticket_data.items():
            if key not in standard_fields and not key.startswith('_') and value:
                # Format key for display
                display_key = key.replace('_', ' ').title()
                extras.append(f"- **{display_key}**: {value}")
        
        if extras:
            additional_text = "\n## ➕ Additional Information\n" + "\n".join(extras) + "\n"
            
        return additional_text 