"""
PromptBuilder Service Package

A standalone microservice for generating AI-optimized prompts from ticket data.
"""

from .service import PromptBuilder, promptbuilder

__version__ = "1.0.0"
__all__ = ["PromptBuilder", "promptbuilder"] 