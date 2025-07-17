"""
PESS Data Normalizer

Stage 2 of the 5-stage pipeline: Validates and normalizes all input data for consistency.
Ensures data quality and applies standardization rules.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import statistics
import re

from ..models.scoring_models import ScoringInput, ScoringStage

logger = logging.getLogger(__name__)

class DataNormalizer:
    """
    Normalizer component for validating and normalizing input data
    """
    
    def __init__(self):
        self.normalization_rules = {
            'retry_count': {'min': 0, 'max': 10},
            'edit_similarity': {'min': 0.0, 'max': 1.0},
            'complexity_score': {'min': 0.0, 'max': 1.0},
            'test_coverage': {'min': 0.0, 'max': 1.0},
            'generation_time': {'min': 0.0, 'max': 3600.0},  # 1 hour max
            'execution_time': {'min': 0.0, 'max': 7200.0}    # 2 hours max
        }
        
        self.quality_thresholds = {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
        
        logger.info("DataNormalizer initialized")
    
    def normalize_data(self, scoring_input: ScoringInput) -> Tuple[ScoringInput, Dict[str, Any]]:
        """
        Normalize and validate scoring input data
        
        Args:
            scoring_input: Input data to normalize
            
        Returns:
            Tuple of (normalized_input, quality_report)
        """
        logger.debug(f"Normalizing data for session {scoring_input.session_id}")
        
        # Create a copy to avoid modifying original
        normalized_input = ScoringInput(**scoring_input.dict())
        
        # Initialize quality report
        quality_report = {
            'data_quality_score': 1.0,
            'normalization_applied': [],
            'validation_warnings': [],
            'field_quality': {},
            'overall_quality': 'high'
        }
        
        # Normalize numeric fields
        self._normalize_numeric_fields(normalized_input, quality_report)
        
        # Normalize string fields
        self._normalize_string_fields(normalized_input, quality_report)
        
        # Normalize list fields
        self._normalize_list_fields(normalized_input, quality_report)
        
        # Validate consistency
        self._validate_consistency(normalized_input, quality_report)
        
        # Calculate overall quality
        self._calculate_overall_quality(quality_report)
        
        # Update metadata
        normalized_input.metadata.update({
            'normalization_timestamp': datetime.utcnow().isoformat(),
            'normalization_version': '1.0',
            'data_quality_score': quality_report['data_quality_score']
        })
        
        logger.info(f"Data normalized for session {scoring_input.session_id}, quality: {quality_report['overall_quality']}")
        return normalized_input, quality_report
    
    def _normalize_numeric_fields(self, scoring_input: ScoringInput, quality_report: Dict[str, Any]) -> None:
        """Normalize numeric fields within acceptable ranges"""
        
        numeric_fields = [
            'retry_count', 'edit_similarity', 'complexity_score', 
            'perf_before', 'perf_after', 'test_coverage', 
            'generation_time', 'execution_time'
        ]
        
        for field in numeric_fields:
            original_value = getattr(scoring_input, field)
            normalized_value = original_value
            field_quality = 1.0
            
            # Apply field-specific normalization rules
            if field in self.normalization_rules:
                rules = self.normalization_rules[field]
                min_val = rules['min']
                max_val = rules['max']
                
                # Clamp values to valid range
                if original_value < min_val:
                    normalized_value = min_val
                    quality_report['normalization_applied'].append(
                        f"{field}: clamped {original_value} to {min_val}"
                    )
                    field_quality = 0.8
                elif original_value > max_val:
                    normalized_value = max_val
                    quality_report['normalization_applied'].append(
                        f"{field}: clamped {original_value} to {max_val}"
                    )
                    field_quality = 0.8
            
            # Special handling for specific fields
            if field == 'retry_count':
                # Retry count should be integer
                if isinstance(original_value, float):
                    normalized_value = int(original_value)
                    quality_report['normalization_applied'].append(
                        f"{field}: converted float to int"
                    )
                    field_quality = 0.9
            
            elif field == 'edit_similarity':
                # Edit similarity should be between 0 and 1
                if original_value > 1.0:
                    # Might be a percentage (0-100)
                    normalized_value = original_value / 100.0
                    quality_report['normalization_applied'].append(
                        f"{field}: converted percentage to decimal"
                    )
                    field_quality = 0.9
            
            elif field in ['perf_before', 'perf_after']:
                # Performance metrics should be non-negative
                if original_value < 0:
                    normalized_value = 0.0
                    quality_report['normalization_applied'].append(
                        f"{field}: converted negative value to 0"
                    )
                    field_quality = 0.7
            
            # Update the field value
            setattr(scoring_input, field, normalized_value)
            quality_report['field_quality'][field] = field_quality
    
    def _normalize_string_fields(self, scoring_input: ScoringInput, quality_report: Dict[str, Any]) -> None:
        """Normalize string fields"""
        
        string_fields = ['session_id', 'ticket_id', 'template_name', 'template_version', 'prompt_hash']
        
        for field in string_fields:
            original_value = getattr(scoring_input, field)
            normalized_value = original_value
            field_quality = 1.0
            
            # Basic string normalization
            if isinstance(original_value, str):
                # Trim whitespace
                normalized_value = original_value.strip()
                
                # Check for empty strings
                if not normalized_value:
                    quality_report['validation_warnings'].append(
                        f"{field}: empty string found"
                    )
                    field_quality = 0.3
                
                # Field-specific validation
                if field == 'session_id':
                    # Session ID should be UUID-like or have minimum length
                    if len(normalized_value) < 8:
                        quality_report['validation_warnings'].append(
                            f"{field}: unusually short session ID"
                        )
                        field_quality = 0.6
                
                elif field == 'ticket_id':
                    # Ticket ID should follow common patterns
                    if not re.match(r'^[A-Z]+-\d+$', normalized_value):
                        quality_report['validation_warnings'].append(
                            f"{field}: unusual ticket ID format"
                        )
                        field_quality = 0.8
                
                elif field == 'template_name':
                    # Template name should be meaningful
                    if len(normalized_value) < 5:
                        quality_report['validation_warnings'].append(
                            f"{field}: very short template name"
                        )
                        field_quality = 0.7
                
                elif field == 'template_version':
                    # Template version should follow semantic versioning
                    if not re.match(r'^\d+\.\d+(\.\d+)?$', normalized_value):
                        quality_report['validation_warnings'].append(
                            f"{field}: non-standard version format"
                        )
                        field_quality = 0.8
                
                elif field == 'prompt_hash':
                    # Prompt hash should be 64-character hex
                    if len(normalized_value) != 64:
                        quality_report['validation_warnings'].append(
                            f"{field}: invalid hash length"
                        )
                        field_quality = 0.3
                    elif not re.match(r'^[a-fA-F0-9]{64}$', normalized_value):
                        quality_report['validation_warnings'].append(
                            f"{field}: invalid hash format"
                        )
                        field_quality = 0.3
                
                # Update field if normalized
                if normalized_value != original_value:
                    setattr(scoring_input, field, normalized_value)
                    quality_report['normalization_applied'].append(
                        f"{field}: trimmed whitespace"
                    )
                    field_quality = min(field_quality, 0.9)
            
            else:
                # Non-string value for string field
                quality_report['validation_warnings'].append(
                    f"{field}: non-string value found"
                )
                field_quality = 0.3
            
            quality_report['field_quality'][field] = field_quality
    
    def _normalize_list_fields(self, scoring_input: ScoringInput, quality_report: Dict[str, Any]) -> None:
        """Normalize list fields"""
        
        # Files referenced list
        if scoring_input.files_referenced:
            original_files = scoring_input.files_referenced
            normalized_files = []
            
            for file_path in original_files:
                if isinstance(file_path, str):
                    # Normalize file path
                    normalized_path = file_path.strip()
                    
                    # Remove duplicates
                    if normalized_path and normalized_path not in normalized_files:
                        normalized_files.append(normalized_path)
                else:
                    quality_report['validation_warnings'].append(
                        f"files_referenced: non-string file path found"
                    )
            
            # Update files list
            scoring_input.files_referenced = normalized_files
            
            # Quality assessment
            if len(normalized_files) != len(original_files):
                quality_report['normalization_applied'].append(
                    f"files_referenced: removed {len(original_files) - len(normalized_files)} invalid/duplicate entries"
                )
                quality_report['field_quality']['files_referenced'] = 0.9
            else:
                quality_report['field_quality']['files_referenced'] = 1.0
    
    def _validate_consistency(self, scoring_input: ScoringInput, quality_report: Dict[str, Any]) -> None:
        """Validate data consistency across fields"""
        
        # Performance consistency
        if scoring_input.perf_before > 0 and scoring_input.perf_after > 0:
            perf_ratio = scoring_input.perf_after / scoring_input.perf_before
            if perf_ratio > 10.0 or perf_ratio < 0.1:
                quality_report['validation_warnings'].append(
                    "performance: extreme performance change detected"
                )
        
        # Time consistency
        if scoring_input.generation_time > scoring_input.execution_time and scoring_input.execution_time > 0:
            quality_report['validation_warnings'].append(
                "timing: generation time exceeds execution time"
            )
        
        # Complexity vs retry consistency
        if scoring_input.complexity_score > 0.8 and scoring_input.retry_count == 0:
            # High complexity with no retries is suspicious
            quality_report['validation_warnings'].append(
                "consistency: high complexity with no retries"
            )
        
        # Edit similarity vs retry consistency
        if scoring_input.edit_similarity < 0.5 and scoring_input.retry_count == 0:
            # Low edit similarity with no retries is suspicious
            quality_report['validation_warnings'].append(
                "consistency: low edit similarity with no retries"
            )
        
        # Test coverage consistency
        if scoring_input.task_type.value == 'test_generation' and scoring_input.test_coverage < 0.1:
            quality_report['validation_warnings'].append(
                "consistency: test generation task with low test coverage"
            )
    
    def _calculate_overall_quality(self, quality_report: Dict[str, Any]) -> None:
        """Calculate overall data quality score"""
        
        # Get all field quality scores
        field_scores = list(quality_report['field_quality'].values())
        
        if field_scores:
            # Calculate weighted average
            avg_field_quality = statistics.mean(field_scores)
            
            # Penalty for warnings
            warning_penalty = len(quality_report['validation_warnings']) * 0.1
            
            # Bonus for successful normalizations
            normalization_bonus = min(len(quality_report['normalization_applied']) * 0.05, 0.2)
            
            # Final score
            final_score = avg_field_quality - warning_penalty + normalization_bonus
            final_score = max(0.0, min(1.0, final_score))
            
            quality_report['data_quality_score'] = final_score
            
            # Determine quality level
            if final_score >= self.quality_thresholds['high']:
                quality_report['overall_quality'] = 'high'
            elif final_score >= self.quality_thresholds['medium']:
                quality_report['overall_quality'] = 'medium'
            else:
                quality_report['overall_quality'] = 'low'
        else:
            quality_report['data_quality_score'] = 0.0
            quality_report['overall_quality'] = 'low'
    
    def batch_normalize(self, scoring_inputs: List[ScoringInput]) -> List[Tuple[ScoringInput, Dict[str, Any]]]:
        """
        Batch normalize multiple scoring inputs
        
        Args:
            scoring_inputs: List of scoring inputs to normalize
            
        Returns:
            List of (normalized_input, quality_report) tuples
        """
        logger.info(f"Batch normalizing {len(scoring_inputs)} inputs")
        
        results = []
        for scoring_input in scoring_inputs:
            try:
                normalized_input, quality_report = self.normalize_data(scoring_input)
                results.append((normalized_input, quality_report))
            except Exception as e:
                logger.error(f"Failed to normalize session {scoring_input.session_id}: {str(e)}")
                # Create error quality report
                error_report = {
                    'data_quality_score': 0.0,
                    'normalization_applied': [],
                    'validation_warnings': [f"Normalization failed: {str(e)}"],
                    'field_quality': {},
                    'overall_quality': 'low'
                }
                results.append((scoring_input, error_report))
        
        logger.info(f"Batch normalization completed for {len(results)} inputs")
        return results
    
    def get_normalization_stats(self) -> Dict[str, Any]:
        """Get normalization statistics and configuration"""
        return {
            'normalization_rules': self.normalization_rules,
            'quality_thresholds': self.quality_thresholds,
            'version': '1.0',
            'supported_fields': [
                'retry_count', 'edit_similarity', 'complexity_score',
                'perf_before', 'perf_after', 'test_coverage',
                'generation_time', 'execution_time', 'files_referenced'
            ]
        } 