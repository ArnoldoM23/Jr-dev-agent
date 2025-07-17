"""
PESS Scoring Pipeline

Main orchestrator for the 5-stage PESS scoring pipeline:
1. Ingestor → 2. Normalizer → 3. Evaluator → 4. Versioner → 5. Emitter

Coordinates the entire scoring process from input to database persistence.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time
from sqlalchemy.orm import Session

from ..models.scoring_models import (
    ScoringInput, ScoringOutput, FeedbackData, ScoringStage
)
from .ingestor import ScoringIngestor
from .normalizer import DataNormalizer
from .evaluator import ScoringEvaluator
from .versioner import ScoreVersioner
from .emitter import ResultEmitter

logger = logging.getLogger(__name__)

class ScoringPipeline:
    """
    Main orchestrator for the 5-stage PESS scoring pipeline
    """
    
    def __init__(self, db_session: Session = None):
        # Initialize all pipeline stages
        self.ingestor = ScoringIngestor()
        self.normalizer = DataNormalizer()
        self.evaluator = ScoringEvaluator()
        self.versioner = ScoreVersioner()
        self.emitter = ResultEmitter(db_session)
        
        # Pipeline configuration
        self.pipeline_config = {
            'enable_batch_processing': True,
            'max_batch_size': 100,
            'pipeline_timeout': 300,  # 5 minutes
            'retry_failed_stages': True,
            'max_retries': 3
        }
        
        # Pipeline statistics
        self.pipeline_stats = {
            'total_processed': 0,
            'successful_completions': 0,
            'failed_completions': 0,
            'avg_processing_time': 0.0,
            'stage_performance': {
                'ingestor': {'success_rate': 0.0, 'avg_time': 0.0},
                'normalizer': {'success_rate': 0.0, 'avg_time': 0.0},
                'evaluator': {'success_rate': 0.0, 'avg_time': 0.0},
                'versioner': {'success_rate': 0.0, 'avg_time': 0.0},
                'emitter': {'success_rate': 0.0, 'avg_time': 0.0}
            }
        }
        
        logger.info("ScoringPipeline initialized with all 5 stages")
    
    def process_scoring_request(self, source: str, input_data: Dict[str, Any], 
                              feedback_data: List[FeedbackData] = None) -> Dict[str, Any]:
        """
        Process a single scoring request through the complete pipeline
        
        Args:
            source: Source of the request ('promptbuilder', 'mcp', 'vscode_extension', 'manual')
            input_data: Raw input data dictionary
            feedback_data: Optional feedback data for enhanced scoring
            
        Returns:
            Pipeline execution result
        """
        pipeline_start_time = time.time()
        session_id = input_data.get('session_id', 'unknown')
        
        logger.info(f"Processing scoring request for session {session_id} from source {source}")
        
        # Initialize result tracking
        pipeline_result = {
            'session_id': session_id,
            'source': source,
            'success': False,
            'stages_completed': [],
            'stage_results': {},
            'final_score': None,
            'processing_time': 0.0,
            'errors': []
        }
        
        try:
            # Stage 1: Ingest
            stage_start_time = time.time()
            scoring_input = self.ingestor.ingest_scoring_request(source, input_data)
            stage_time = time.time() - stage_start_time
            
            pipeline_result['stages_completed'].append('ingestor')
            pipeline_result['stage_results']['ingestor'] = {
                'success': True,
                'processing_time': stage_time,
                'output': 'ScoringInput object created'
            }
            
            # Stage 2: Normalize
            stage_start_time = time.time()
            normalized_input, quality_report = self.normalizer.normalize_data(scoring_input)
            stage_time = time.time() - stage_start_time
            
            pipeline_result['stages_completed'].append('normalizer')
            pipeline_result['stage_results']['normalizer'] = {
                'success': True,
                'processing_time': stage_time,
                'output': f"Data quality: {quality_report['overall_quality']}"
            }
            
            # Stage 3: Evaluate
            stage_start_time = time.time()
            scoring_output = self.evaluator.evaluate_score(normalized_input, quality_report, feedback_data)
            stage_time = time.time() - stage_start_time
            
            pipeline_result['stages_completed'].append('evaluator')
            pipeline_result['stage_results']['evaluator'] = {
                'success': True,
                'processing_time': stage_time,
                'output': f"Final score: {scoring_output.metrics.final_score:.2f}"
            }
            
            # Stage 4: Version
            stage_start_time = time.time()
            versioned_output = self.versioner.version_score(scoring_output)
            stage_time = time.time() - stage_start_time
            
            pipeline_result['stages_completed'].append('versioner')
            pipeline_result['stage_results']['versioner'] = {
                'success': True,
                'processing_time': stage_time,
                'output': f"Version: {versioned_output.score_version}"
            }
            
            # Stage 5: Emit
            stage_start_time = time.time()
            emission_result = self.emitter.emit_result(versioned_output)
            stage_time = time.time() - stage_start_time
            
            pipeline_result['stages_completed'].append('emitter')
            pipeline_result['stage_results']['emitter'] = {
                'success': emission_result.get('database_saved', False),
                'processing_time': stage_time,
                'output': f"Database saved: {emission_result.get('database_saved', False)}"
            }
            
            # Pipeline completion
            pipeline_result['success'] = True
            pipeline_result['final_score'] = versioned_output.metrics.final_score
            pipeline_result['scoring_output'] = versioned_output
            
            # Update statistics
            self._update_pipeline_stats(pipeline_result, time.time() - pipeline_start_time)
            
            logger.info(f"Pipeline completed successfully for session {session_id}, "
                       f"score: {versioned_output.metrics.final_score:.2f}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for session {session_id}: {str(e)}")
            pipeline_result['errors'].append(str(e))
            self._update_pipeline_stats(pipeline_result, time.time() - pipeline_start_time, success=False)
        
        finally:
            pipeline_result['processing_time'] = time.time() - pipeline_start_time
        
        return pipeline_result
    
    def batch_process_scoring_requests(self, requests: List[Tuple[str, Dict[str, Any], List[FeedbackData]]]
                                     ) -> List[Dict[str, Any]]:
        """
        Process multiple scoring requests in batch
        
        Args:
            requests: List of (source, input_data, feedback_data) tuples
            
        Returns:
            List of pipeline execution results
        """
        logger.info(f"Starting batch processing for {len(requests)} requests")
        
        batch_results = []
        
        if self.pipeline_config['enable_batch_processing'] and len(requests) > 1:
            # Use optimized batch processing
            batch_results = self._process_batch_optimized(requests)
        else:
            # Process individually
            for source, input_data, feedback_data in requests:
                result = self.process_scoring_request(source, input_data, feedback_data)
                batch_results.append(result)
        
        logger.info(f"Batch processing completed for {len(batch_results)} requests")
        return batch_results
    
    def _process_batch_optimized(self, requests: List[Tuple[str, Dict[str, Any], List[FeedbackData]]]
                               ) -> List[Dict[str, Any]]:
        """Optimized batch processing using pipeline stage batching"""
        
        batch_start_time = time.time()
        logger.info(f"Starting optimized batch processing for {len(requests)} requests")
        
        # Stage 1: Batch Ingest
        ingested_inputs = []
        ingest_results = []
        
        for source, input_data, feedback_data in requests:
            try:
                scoring_input = self.ingestor.ingest_scoring_request(source, input_data)
                ingested_inputs.append((scoring_input, feedback_data))
                ingest_results.append({'success': True, 'session_id': scoring_input.session_id})
            except Exception as e:
                logger.error(f"Batch ingest failed for request: {str(e)}")
                ingest_results.append({'success': False, 'error': str(e)})
        
        # Stage 2: Batch Normalize
        normalized_results = []
        if ingested_inputs:
            scoring_inputs = [item[0] for item in ingested_inputs]
            normalization_results = self.normalizer.batch_normalize(scoring_inputs)
            normalized_results = [(norm_input, quality_report, feedback) 
                                for (norm_input, quality_report), (_, feedback) 
                                in zip(normalization_results, ingested_inputs)]
        
        # Stage 3: Batch Evaluate
        evaluated_outputs = []
        if normalized_results:
            eval_inputs = [(norm_input, quality_report) for norm_input, quality_report, _ in normalized_results]
            feedback_map = {norm_input.session_id: feedback for norm_input, _, feedback in normalized_results}
            evaluated_outputs = self.evaluator.batch_evaluate(eval_inputs, feedback_map)
        
        # Stage 4: Batch Version
        versioned_outputs = []
        if evaluated_outputs:
            versioned_outputs = self.versioner.batch_version(evaluated_outputs)
        
        # Stage 5: Batch Emit
        emission_results = []
        if versioned_outputs:
            emission_results = self.emitter.batch_emit(versioned_outputs)
        
        # Compile final results
        final_results = []
        for i, (source, input_data, feedback_data) in enumerate(requests):
            session_id = input_data.get('session_id', 'unknown')
            
            if i < len(emission_results):
                result = {
                    'session_id': session_id,
                    'source': source,
                    'success': emission_results[i].get('database_saved', False),
                    'stages_completed': ['ingestor', 'normalizer', 'evaluator', 'versioner', 'emitter'],
                    'final_score': versioned_outputs[i].metrics.final_score if i < len(versioned_outputs) else None,
                    'scoring_output': versioned_outputs[i] if i < len(versioned_outputs) else None,
                    'processing_time': time.time() - batch_start_time,
                    'errors': emission_results[i].get('errors', [])
                }
            else:
                result = {
                    'session_id': session_id,
                    'source': source,
                    'success': False,
                    'stages_completed': [],
                    'errors': ['Failed in early pipeline stage']
                }
            
            final_results.append(result)
        
        logger.info(f"Optimized batch processing completed in {time.time() - batch_start_time:.2f}s")
        return final_results
    
    def _update_pipeline_stats(self, pipeline_result: Dict[str, Any], 
                             processing_time: float, success: bool = True) -> None:
        """Update pipeline statistics"""
        
        self.pipeline_stats['total_processed'] += 1
        
        if success:
            self.pipeline_stats['successful_completions'] += 1
        else:
            self.pipeline_stats['failed_completions'] += 1
        
        # Update average processing time
        current_avg = self.pipeline_stats['avg_processing_time']
        total_processed = self.pipeline_stats['total_processed']
        
        new_avg = ((current_avg * (total_processed - 1)) + processing_time) / total_processed
        self.pipeline_stats['avg_processing_time'] = new_avg
        
        # Update stage performance statistics
        for stage_name in ['ingestor', 'normalizer', 'evaluator', 'versioner', 'emitter']:
            if stage_name in pipeline_result.get('stage_results', {}):
                stage_result = pipeline_result['stage_results'][stage_name]
                stage_stats = self.pipeline_stats['stage_performance'][stage_name]
                
                # Update success rate (simplified calculation)
                if stage_result.get('success', False):
                    stage_stats['success_rate'] = min(1.0, stage_stats['success_rate'] + 0.01)
                else:
                    stage_stats['success_rate'] = max(0.0, stage_stats['success_rate'] - 0.01)
                
                # Update average time
                stage_time = stage_result.get('processing_time', 0.0)
                if stage_time > 0:
                    current_stage_avg = stage_stats['avg_time']
                    stage_stats['avg_time'] = ((current_stage_avg * 9) + stage_time) / 10  # Moving average
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get comprehensive pipeline health status"""
        
        health_status = {
            'overall_status': 'healthy',
            'pipeline_stats': self.pipeline_stats,
            'stage_health': {},
            'recommendations': []
        }
        
        # Check individual stage health
        for stage_name in ['ingestor', 'normalizer', 'evaluator', 'versioner', 'emitter']:
            stage_stats = self.pipeline_stats['stage_performance'][stage_name]
            
            if stage_stats['success_rate'] < 0.9:
                health_status['stage_health'][stage_name] = 'unhealthy'
                health_status['recommendations'].append(f"Investigate {stage_name} stage performance")
            elif stage_stats['success_rate'] < 0.95:
                health_status['stage_health'][stage_name] = 'warning'
            else:
                health_status['stage_health'][stage_name] = 'healthy'
        
        # Overall health assessment
        unhealthy_stages = [k for k, v in health_status['stage_health'].items() if v == 'unhealthy']
        if unhealthy_stages:
            health_status['overall_status'] = 'unhealthy'
        elif any(v == 'warning' for v in health_status['stage_health'].values()):
            health_status['overall_status'] = 'warning'
        
        # Add component health
        health_status['component_health'] = {
            'ingestor': self.ingestor.get_ingestion_stats(),
            'normalizer': self.normalizer.get_normalization_stats(),
            'evaluator': self.evaluator.get_evaluation_stats(),
            'versioner': self.versioner.get_versioning_stats(),
            'emitter': self.emitter.get_emission_stats()
        }
        
        return health_status
    
    def configure_pipeline(self, config: Dict[str, Any]) -> None:
        """Configure pipeline settings"""
        
        self.pipeline_config.update(config)
        logger.info(f"Pipeline configuration updated: {config}")
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        
        total_processed = self.pipeline_stats['total_processed']
        
        return {
            'pipeline_stats': self.pipeline_stats,
            'success_rate': (self.pipeline_stats['successful_completions'] / total_processed 
                           if total_processed > 0 else 0.0),
            'failure_rate': (self.pipeline_stats['failed_completions'] / total_processed 
                           if total_processed > 0 else 0.0),
            'pipeline_config': self.pipeline_config,
            'stage_metrics': {
                'ingestor': self.ingestor.get_ingestion_stats(),
                'normalizer': self.normalizer.get_normalization_stats(),
                'evaluator': self.evaluator.get_evaluation_stats(),
                'versioner': self.versioner.get_versioning_stats(),
                'emitter': self.emitter.get_emission_stats()
            }
        }
    
    def reset_pipeline_stats(self) -> None:
        """Reset pipeline statistics"""
        
        self.pipeline_stats = {
            'total_processed': 0,
            'successful_completions': 0,
            'failed_completions': 0,
            'avg_processing_time': 0.0,
            'stage_performance': {
                'ingestor': {'success_rate': 0.0, 'avg_time': 0.0},
                'normalizer': {'success_rate': 0.0, 'avg_time': 0.0},
                'evaluator': {'success_rate': 0.0, 'avg_time': 0.0},
                'versioner': {'success_rate': 0.0, 'avg_time': 0.0},
                'emitter': {'success_rate': 0.0, 'avg_time': 0.0}
            }
        }
        
        logger.info("Pipeline statistics reset")
    
    def process_feedback(self, feedback_data: FeedbackData) -> Dict[str, Any]:
        """Process feedback data for scoring improvement"""
        
        logger.info(f"Processing feedback for session {feedback_data.session_id}")
        
        # Store feedback for future scoring requests
        # This would typically involve saving to database or cache
        
        return {
            'feedback_id': feedback_data.feedback_id,
            'session_id': feedback_data.session_id,
            'processed': True,
            'timestamp': datetime.utcnow().isoformat()
        } 