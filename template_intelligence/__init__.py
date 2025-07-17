"""
Template Intelligence Service Package

A standalone microservice for intelligent template selection and management.
"""

from .engine.template_engine import TemplateEngine, template_engine

__version__ = "1.0.0"
__all__ = ["TemplateEngine", "template_engine"] 