"""
PESS Scoring Evaluator

Stage 3 of the 5-stage pipeline: Generates scores across 8 evaluation dimensions.
Uses the ScoringAlgorithm to calculate comprehensive scoring metrics.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time

from ..models.scoring_models import (
    ScoringInput, ScoringOutput, ScoringMetrics, FeedbackData, ScoringStage
)
from .scoring_algorithm import ScoringAlgorithm

logger = logging.getLogger(__name__)

class ScoringEvaluator:
    """
    Evaluator component for generating 8-dimensional scores
    """
    
    def __init__(self):
        self.scoring_algorithm = ScoringAlgorithm()
        self.evaluation_stage = ScoringStage.EVALUATOR
        
        # Performance tracking
        self.evaluation_stats = {
            'total_evaluations': 0,
            'avg_processing_time': 0.0,
            'success_rate': 0.0,
            'last_evaluation': None
        }
        
        logger.info("ScoringEvaluator initialized")
    
    def evaluate_score(self, scoring_input: ScoringInput, 
                      data_quality_report: Dict[str, Any],
                      feedback_data: List[FeedbackData] = None) -> ScoringOutput:
        """
        Evaluate scoring input to generate comprehensive scoring metrics
        
        Args:
            scoring_input: Normalized input data
            data_quality_report: Quality report from normalizer
            feedback_data: Optional feedback data for enhanced scoring
            
        Returns:
            ScoringOutput with comprehensive metrics
        """
        start_time = time.time()
        logger.debug(f"Evaluating score for session {scoring_input.session_id}")
        
        try:
            # Calculate scoring metrics using the algorithm
            metrics = self._calculate_scoring_metrics(scoring_input, feedback_data)
            
            # Generate recommendations and alerts
            recommendations = self._generate_recommendations(scoring_input, metrics)
            alerts = self._generate_alerts(scoring_input, metrics)
            
            # Calculate confidence and quality scores
            confidence_score = self._calculate_confidence_score(scoring_input, data_quality_report)
            data_quality = data_quality_report.get('data_quality_score', 1.0)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create scoring output
            scoring_output = ScoringOutput(
                session_id=scoring_input.session_id,
                metrics=metrics,
                pipeline_stage=self.evaluation_stage,
                processing_time=processing_time,
                confidence_score=confidence_score,
                data_quality=data_quality,
                recommendations=recommendations,
                alerts=alerts
            )
            
            # Update evaluation metadata
            scoring_output.template_correlation = {
                'template_name': scoring_input.template_name,
                'template_version': scoring_input.template_version,
                'prompt_hash': scoring_input.prompt_hash,
                'task_type': scoring_input.task_type.value
            }
            
            # Update statistics
            self._update_evaluation_stats(processing_time, success=True)
            
            logger.info(f"Score evaluation completed for session {scoring_input.session_id}, "
                       f"final score: {metrics.final_score:.2f}")
            
            return scoring_output
            
        except Exception as e:
            logger.error(f"Failed to evaluate score for session {scoring_input.session_id}: {str(e)}")
            self._update_evaluation_stats(time.time() - start_time, success=False)
            raise
    
    def _calculate_scoring_metrics(self, scoring_input: ScoringInput, 
                                 feedback_data: List[FeedbackData] = None) -> ScoringMetrics:
        """Calculate comprehensive scoring metrics"""
        
        # Use the scoring algorithm to calculate metrics
        metrics = self.scoring_algorithm.calculate_score(scoring_input, feedback_data)
        
        return metrics
    
    def _generate_recommendations(self, scoring_input: ScoringInput, 
                                metrics: ScoringMetrics) -> List[str]:
        """Generate improvement recommendations based on scoring results"""
        
        recommendations = []
        dimensional_scores = metrics.dimensional_scores
        
        # Clarity recommendations
        if dimensional_scores.clarity < 0.7:
            recommendations.append("Improve template structure and instruction clarity")
        
        # Coverage recommendations
        if dimensional_scores.coverage < 0.6:
            recommendations.append("Include more relevant file references and test cases")
        
        # Retry penalty recommendations
        if dimensional_scores.retry_penalty < 0.5:
            recommendations.append("Reduce retry attempts by improving initial prompt quality")
        
        # Edit penalty recommendations
        if dimensional_scores.edit_penalty < 0.6:
            recommendations.append("Minimize manual edits by improving code generation accuracy")
        
        # Complexity handling recommendations
        if dimensional_scores.complexity_handling < 0.6:
            recommendations.append("Better handle task complexity with more detailed prompts")
        
        # Performance impact recommendations
        if dimensional_scores.performance_impact < 0.5:
            recommendations.append("Monitor and optimize performance impact of generated code")
        
        # Review quality recommendations
        if dimensional_scores.review_quality < 0.7:
            recommendations.append("Focus on generating code that passes review with minimal feedback")
        
        # Developer satisfaction recommendations
        if dimensional_scores.developer_satisfaction < 0.6:
            recommendations.append("Gather more developer feedback to improve satisfaction")
        
        # General recommendations based on final score
        if metrics.final_score < 60:
            recommendations.append("Consider revising template or prompt generation strategy")
        elif metrics.final_score < 80:
            recommendations.append("Minor improvements needed to reach optimal performance")
        
        return recommendations
    
    def _generate_alerts(self, scoring_input: ScoringInput, 
                        metrics: ScoringMetrics) -> List[str]:
        """Generate alerts for concerning scoring patterns"""
        
        alerts = []
        dimensional_scores = metrics.dimensional_scores
        
        # Critical score alerts
        if metrics.final_score < 40:
            alerts.append("CRITICAL: Very low final score detected")
        
        # High retry alerts
        if scoring_input.retry_count >= 3:
            alerts.append("HIGH: Multiple retries detected - template may need revision")
        
        # Poor edit similarity alerts
        if dimensional_scores.edit_penalty < 0.3:
            alerts.append("HIGH: Significant manual edits required")
        
        # Performance regression alerts
        if dimensional_scores.performance_impact < 0.4:
            alerts.append("MEDIUM: Performance regression detected")
        
        # Quality consistency alerts
        if dimensional_scores.review_quality < 0.5:
            alerts.append("MEDIUM: Poor review quality - code quality concerns")
        
        # Template-specific alerts
        if dimensional_scores.clarity < 0.4:
            alerts.append("HIGH: Template clarity issues detected")
        
        # Coverage alerts
        if dimensional_scores.coverage < 0.3:
            alerts.append("MEDIUM: Poor test and file coverage")
        
        # Complexity handling alerts
        if (scoring_input.complexity_score > 0.8 and 
            dimensional_scores.complexity_handling < 0.5):
            alerts.append("HIGH: Complex task handled poorly")
        
        return alerts
    
    def _calculate_confidence_score(self, scoring_input: ScoringInput, 
                                  data_quality_report: Dict[str, Any]) -> float:
        """Calculate confidence score for the evaluation"""
        
        confidence = 1.0
        
        # Reduce confidence based on data quality
        data_quality = data_quality_report.get('data_quality_score', 1.0)
        confidence *= data_quality
        
        # Reduce confidence for missing or limited data
        if not scoring_input.files_referenced:
            confidence *= 0.9
        
        if scoring_input.test_coverage == 0:
            confidence *= 0.9
        
        if scoring_input.generation_time == 0:
            confidence *= 0.95
        
        if scoring_input.execution_time == 0:
            confidence *= 0.95
        
        # Reduce confidence for extreme values
        if scoring_input.retry_count > 5:
            confidence *= 0.8
        
        if scoring_input.edit_similarity < 0.3:
            confidence *= 0.8
        
        # Warnings from data quality reduce confidence
        warning_count = len(data_quality_report.get('validation_warnings', []))
        if warning_count > 0:
            confidence *= max(0.7, 1.0 - (warning_count * 0.1))
        
        return max(0.0, min(1.0, confidence))
    
    def _update_evaluation_stats(self, processing_time: float, success: bool) -> None:
        """Update evaluation statistics"""
        
        self.evaluation_stats['total_evaluations'] += 1
        self.evaluation_stats['last_evaluation'] = datetime.utcnow().isoformat()
        
        # Update average processing time
        current_avg = self.evaluation_stats['avg_processing_time']
        total_evals = self.evaluation_stats['total_evaluations']
        
        new_avg = ((current_avg * (total_evals - 1)) + processing_time) / total_evals
        self.evaluation_stats['avg_processing_time'] = new_avg
        
        # Update success rate
        if success:
            current_success_rate = self.evaluation_stats.get('success_count', 0)
            self.evaluation_stats['success_count'] = current_success_rate + 1
        
        success_count = self.evaluation_stats.get('success_count', 0)
        self.evaluation_stats['success_rate'] = success_count / total_evals
    
    def batch_evaluate(self, scoring_inputs: List[Tuple[ScoringInput, Dict[str, Any]]], 
                      feedback_data_map: Dict[str, List[FeedbackData]] = None) -> List[ScoringOutput]:
        """
        Batch evaluate multiple scoring inputs
        
        Args:
            scoring_inputs: List of (scoring_input, quality_report) tuples
            feedback_data_map: Optional mapping of session_id to feedback data
            
        Returns:
            List of ScoringOutput objects
        """
        logger.info(f"Batch evaluating {len(scoring_inputs)} inputs")
        
        results = []
        feedback_data_map = feedback_data_map or {}
        
        for scoring_input, quality_report in scoring_inputs:
            try:
                session_feedback = feedback_data_map.get(scoring_input.session_id, [])
                scoring_output = self.evaluate_score(scoring_input, quality_report, session_feedback)
                results.append(scoring_output)
            except Exception as e:
                logger.error(f"Failed to evaluate session {scoring_input.session_id}: {str(e)}")
                # Create error output
                error_output = ScoringOutput(
                    session_id=scoring_input.session_id,
                    metrics=ScoringMetrics(
                        base_score=0.0,
                        final_score=0.0,
                        dimensional_scores=self._get_default_dimensional_scores()
                    ),
                    pipeline_stage=self.evaluation_stage,
                    processing_time=0.0,
                    confidence_score=0.0,
                    data_quality=0.0,
                    recommendations=[],
                    alerts=[f"Evaluation failed: {str(e)}"]
                )
                results.append(error_output)
        
        logger.info(f"Batch evaluation completed for {len(results)} inputs")
        return results
    
    def _get_default_dimensional_scores(self):
        """Get default dimensional scores for error cases"""
        from ..models.scoring_models import DimensionalScores
        return DimensionalScores(
            clarity=0.0,
            coverage=0.0,
            retry_penalty=0.0,
            edit_penalty=0.0,
            complexity_handling=0.0,
            performance_impact=0.0,
            review_quality=0.0,
            developer_satisfaction=0.0
        )
    
    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        return {
            **self.evaluation_stats,
            'algorithm_version': self.scoring_algorithm.algorithm_version,
            'stage': self.evaluation_stage.value,
            'version': '1.0'
        }
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get scoring algorithm information"""
        return self.scoring_algorithm.get_algorithm_info() 