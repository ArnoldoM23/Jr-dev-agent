"""
PESS Core Components

Core pipeline components for the 5-stage PESS scoring system:
- Ingestor: Accepts structured input from PromptBuilder, MCP, and VS Code Extension
- Normalizer: Validates and normalizes all input data for consistency
- Evaluator: Generates scores across 8 evaluation dimensions
- Versioner: Versions all scores with template and hash correlation
- Emitter: Emits results to database and downstream systems
"""

from .ingestor import ScoringIngestor
from .normalizer import DataNormalizer
from .evaluator import ScoringEvaluator
from .versioner import ScoreVersioner
from .emitter import ResultEmitter
from .pipeline import ScoringPipeline
from .scoring_algorithm import ScoringAlgorithm

__all__ = [
    "ScoringIngestor",
    "DataNormalizer", 
    "ScoringEvaluator",
    "ScoreVersioner",
    "ResultEmitter",
    "ScoringPipeline",
    "ScoringAlgorithm"
] 