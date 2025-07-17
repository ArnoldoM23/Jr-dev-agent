"""
PESS Scoring Ingestor

Stage 1 of the 5-stage pipeline: Accepts structured input from PromptBuilder, MCP, and VS Code Extension.
Validates input format and prepares data for the pipeline.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib

from ..models.scoring_models import ScoringInput, ScoringStage, TaskType

logger = logging.getLogger(__name__)

class ScoringIngestor:
    """
    Ingestor component for accepting structured input from multiple sources
    """
    
    def __init__(self):
        self.supported_sources = ['promptbuilder', 'mcp', 'vscode_extension', 'manual']
        self.required_fields = [
            'session_id', 'ticket_id', 'task_type', 'template_name', 
            'template_version', 'prompt_hash'
        ]
        
        logger.info("ScoringIngestor initialized")
    
    def ingest_scoring_request(self, source: str, data: Dict[str, Any]) -> ScoringInput:
        """
        Ingest scoring request from various sources
        
        Args:
            source: Source of the request ('promptbuilder', 'mcp', 'vscode_extension', 'manual')
            data: Raw input data dictionary
            
        Returns:
            ScoringInput object ready for pipeline processing
            
        Raises:
            ValueError: If source is not supported or data is invalid
        """
        logger.debug(f"Ingesting scoring request from source: {source}")
        
        # Validate source
        if source not in self.supported_sources:
            raise ValueError(f"Unsupported source: {source}. Supported sources: {self.supported_sources}")
        
        # Validate and normalize data based on source
        normalized_data = self._normalize_by_source(source, data)
        
        # Validate required fields
        self._validate_required_fields(normalized_data)
        
        # Create ScoringInput object
        scoring_input = self._create_scoring_input(normalized_data)
        
        # Add ingestion metadata
        scoring_input.metadata.update({
            'ingestion_source': source,
            'ingestion_timestamp': datetime.utcnow().isoformat(),
            'ingestion_version': '1.0'
        })
        
        logger.info(f"Successfully ingested scoring request for session {scoring_input.session_id}")
        return scoring_input
    
    def _normalize_by_source(self, source: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data based on source format"""
        
        if source == 'promptbuilder':
            return self._normalize_promptbuilder_data(data)
        elif source == 'mcp':
            return self._normalize_mcp_data(data)
        elif source == 'vscode_extension':
            return self._normalize_vscode_data(data)
        elif source == 'manual':
            return self._normalize_manual_data(data)
        else:
            return data
    
    def _normalize_promptbuilder_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data from PromptBuilder service"""
        normalized = {}
        
        # Map PromptBuilder fields to standard fields
        field_mapping = {
            'sessionId': 'session_id',
            'ticketId': 'ticket_id',
            'taskType': 'task_type',
            'templateName': 'template_name',
            'templateVersion': 'template_version',
            'promptHash': 'prompt_hash',
            'retryCount': 'retry_count',
            'editSimilarity': 'edit_similarity',
            'complexityScore': 'complexity_score',
            'perfBefore': 'perf_before',
            'perfAfter': 'perf_after',
            'filesReferenced': 'files_referenced',
            'testCoverage': 'test_coverage',
            'generationTime': 'generation_time',
            'executionTime': 'execution_time'
        }
        
        for pb_field, standard_field in field_mapping.items():
            if pb_field in data:
                normalized[standard_field] = data[pb_field]
        
        # Handle nested metadata
        if 'metadata' in data:
            normalized['metadata'] = data['metadata']
        
        logger.debug("Normalized PromptBuilder data")
        return normalized
    
    def _normalize_mcp_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data from MCP server"""
        normalized = {}
        
        # MCP typically sends data in a structured format
        if 'scoring_request' in data:
            request_data = data['scoring_request']
            
            # Extract standard fields
            for field in self.required_fields:
                if field in request_data:
                    normalized[field] = request_data[field]
            
            # Extract metrics
            if 'metrics' in request_data:
                metrics = request_data['metrics']
                normalized.update({
                    'retry_count': metrics.get('retry_count', 0),
                    'edit_similarity': metrics.get('edit_similarity', 1.0),
                    'complexity_score': metrics.get('complexity_score', 0.5),
                    'perf_before': metrics.get('perf_before', 0.0),
                    'perf_after': metrics.get('perf_after', 0.0),
                    'test_coverage': metrics.get('test_coverage', 0.0),
                    'generation_time': metrics.get('generation_time', 0.0),
                    'execution_time': metrics.get('execution_time', 0.0)
                })
            
            # Extract file references
            if 'files_referenced' in request_data:
                normalized['files_referenced'] = request_data['files_referenced']
            
            # Extract metadata
            if 'metadata' in request_data:
                normalized['metadata'] = request_data['metadata']
        
        logger.debug("Normalized MCP data")
        return normalized
    
    def _normalize_vscode_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data from VS Code extension"""
        normalized = {}
        
        # VS Code extension format
        if 'scoring_data' in data:
            scoring_data = data['scoring_data']
            
            # Direct mapping for most fields
            for field in self.required_fields:
                if field in scoring_data:
                    normalized[field] = scoring_data[field]
            
            # Handle metrics
            if 'metrics' in scoring_data:
                normalized.update(scoring_data['metrics'])
            
            # Handle files
            if 'files' in scoring_data:
                normalized['files_referenced'] = scoring_data['files']
            
            # Handle metadata
            normalized['metadata'] = scoring_data.get('metadata', {})
            normalized['metadata'].update({
                'vscode_version': data.get('vscode_version'),
                'extension_version': data.get('extension_version')
            })
        
        logger.debug("Normalized VS Code data")
        return normalized
    
    def _normalize_manual_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize manually provided data"""
        # Manual data should already be in correct format
        # Just ensure types are correct
        normalized = dict(data)
        
        # Ensure task_type is enum
        if 'task_type' in normalized:
            task_type = normalized['task_type']
            if isinstance(task_type, str):
                try:
                    normalized['task_type'] = TaskType(task_type.lower())
                except ValueError:
                    logger.warning(f"Unknown task type: {task_type}, defaulting to 'feature'")
                    normalized['task_type'] = TaskType.FEATURE
        
        logger.debug("Normalized manual data")
        return normalized
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Validate that all required fields are present"""
        missing_fields = []
        
        for field in self.required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Additional validation
        self._validate_field_types(data)
    
    def _validate_field_types(self, data: Dict[str, Any]) -> None:
        """Validate field types"""
        
        # String fields
        string_fields = ['session_id', 'ticket_id', 'template_name', 'template_version', 'prompt_hash']
        for field in string_fields:
            if field in data and not isinstance(data[field], str):
                raise ValueError(f"Field {field} must be a string")
        
        # Numeric fields
        numeric_fields = {
            'retry_count': int,
            'edit_similarity': float,
            'complexity_score': float,
            'perf_before': float,
            'perf_after': float,
            'test_coverage': float,
            'generation_time': float,
            'execution_time': float
        }
        
        for field, expected_type in numeric_fields.items():
            if field in data:
                try:
                    if expected_type == int:
                        data[field] = int(data[field])
                    else:
                        data[field] = float(data[field])
                except (ValueError, TypeError):
                    raise ValueError(f"Field {field} must be numeric")
        
        # Validate prompt hash format
        if 'prompt_hash' in data:
            prompt_hash = data['prompt_hash']
            if len(prompt_hash) != 64:
                raise ValueError("prompt_hash must be a 64-character SHA256 hash")
    
    def _create_scoring_input(self, data: Dict[str, Any]) -> ScoringInput:
        """Create ScoringInput object from normalized data"""
        
        # Handle task type conversion
        task_type = data['task_type']
        if isinstance(task_type, str):
            task_type = TaskType(task_type.lower())
        
        # Create ScoringInput with all available fields
        scoring_input = ScoringInput(
            session_id=data['session_id'],
            ticket_id=data['ticket_id'],
            task_type=task_type,
            template_name=data['template_name'],
            template_version=data['template_version'],
            prompt_hash=data['prompt_hash'],
            retry_count=data.get('retry_count', 0),
            edit_similarity=data.get('edit_similarity', 1.0),
            complexity_score=data.get('complexity_score', 0.5),
            perf_before=data.get('perf_before', 0.0),
            perf_after=data.get('perf_after', 0.0),
            files_referenced=data.get('files_referenced', []),
            test_coverage=data.get('test_coverage', 0.0),
            generation_time=data.get('generation_time', 0.0),
            execution_time=data.get('execution_time', 0.0),
            metadata=data.get('metadata', {})
        )
        
        return scoring_input
    
    def batch_ingest(self, source: str, data_list: List[Dict[str, Any]]) -> List[ScoringInput]:
        """
        Batch ingest multiple scoring requests
        
        Args:
            source: Source of the requests
            data_list: List of raw input data dictionaries
            
        Returns:
            List of ScoringInput objects
        """
        logger.info(f"Batch ingesting {len(data_list)} requests from {source}")
        
        results = []
        errors = []
        
        for i, data in enumerate(data_list):
            try:
                scoring_input = self.ingest_scoring_request(source, data)
                results.append(scoring_input)
            except Exception as e:
                error_msg = f"Failed to ingest item {i}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Batch ingestion completed: {len(results)} successful, {len(errors)} errors")
        
        if errors:
            logger.warning(f"Batch ingestion errors: {errors}")
        
        return results
    
    def validate_prompt_hash(self, prompt_content: str) -> str:
        """
        Generate and validate prompt hash
        
        Args:
            prompt_content: Raw prompt content
            
        Returns:
            SHA256 hash of the prompt content
        """
        if not prompt_content:
            raise ValueError("Prompt content cannot be empty")
        
        # Generate SHA256 hash
        hash_object = hashlib.sha256(prompt_content.encode('utf-8'))
        prompt_hash = hash_object.hexdigest()
        
        logger.debug(f"Generated prompt hash: {prompt_hash}")
        return prompt_hash
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        return {
            'supported_sources': self.supported_sources,
            'required_fields': self.required_fields,
            'version': '1.0',
            'last_updated': datetime.utcnow().isoformat()
        } 