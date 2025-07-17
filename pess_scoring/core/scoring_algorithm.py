"""
PESS Scoring Algorithm

Core algorithm for calculating 8-dimensional scores as specified in requirements:
- Clarity: Template structure and instruction completeness
- Coverage: File references and test case inclusion
- Retry Penalty: Deduct points based on retry attempts
- Edit Penalty: Reduce score for manual developer edits
- Complexity Handling: Adjust scoring based on task complexity
- Performance Impact: Measure before/after operation metrics
- Review Quality: Analyze PR review feedback and approval rates
- Developer Satisfaction: Incorporate manual feedback and ratings
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math

from ..models.scoring_models import (
    ScoringInput, 
    DimensionalScores, 
    ScoringMetrics, 
    FeedbackData,
    FeedbackType
)

logger = logging.getLogger(__name__)

class ScoringAlgorithm:
    """Core scoring algorithm implementing 8-dimensional scoring system"""
    
    def __init__(self):
        self.algorithm_version = "1.0"
        self.base_score = 100.0
        
        # Weight factors for dimensional scoring
        self.dimension_weights = {
            'clarity': 0.15,
            'coverage': 0.15,
            'retry_penalty': 0.20,
            'edit_penalty': 0.15,
            'complexity_handling': 0.10,
            'performance_impact': 0.10,
            'review_quality': 0.10,
            'developer_satisfaction': 0.05
        }
        
        # Penalty factors
        self.retry_penalty_factor = 10.0  # Points deducted per retry
        self.edit_penalty_threshold = 0.7  # Similarity threshold for penalties
        self.edit_penalty_points = 20.0
        self.performance_penalty_points = 15.0
        
        # Complexity adjustment factors
        self.complexity_bonus_factor = 0.1  # 10% bonus for complex tasks
        
        logger.info(f"ScoringAlgorithm initialized with version {self.algorithm_version}")
    
    def calculate_score(self, input_data: ScoringInput, feedback_data: List[FeedbackData] = None) -> ScoringMetrics:
        """
        Calculate comprehensive scoring metrics using the 8-dimensional system
        
        Args:
            input_data: Input data for scoring
            feedback_data: Optional feedback data for enhanced scoring
            
        Returns:
            ScoringMetrics with detailed dimensional scores
        """
        logger.debug(f"Calculating score for session {input_data.session_id}")
        
        # Calculate base score
        base_score = self.base_score
        
        # Calculate each dimension
        dimensional_scores = self._calculate_dimensional_scores(input_data, feedback_data)
        
        # Apply penalties and adjustments
        penalties = self._calculate_penalties(input_data)
        bonuses = self._calculate_bonuses(input_data)
        adjustments = self._calculate_adjustments(input_data, dimensional_scores)
        
        # Calculate final score
        final_score = self._calculate_final_score(
            base_score, dimensional_scores, penalties, bonuses, adjustments
        )
        
        # Create metrics object
        metrics = ScoringMetrics(
            base_score=base_score,
            final_score=final_score,
            dimensional_scores=dimensional_scores,
            adjustments=adjustments,
            penalties=penalties,
            bonuses=bonuses
        )
        
        logger.debug(f"Score calculated: {final_score:.2f}/100.0")
        return metrics
    
    def _calculate_dimensional_scores(self, input_data: ScoringInput, feedback_data: List[FeedbackData] = None) -> DimensionalScores:
        """Calculate all 8 dimensional scores"""
        
        # 1. Clarity: Template structure and instruction completeness
        clarity = self._calculate_clarity(input_data)
        
        # 2. Coverage: File references and test case inclusion
        coverage = self._calculate_coverage(input_data)
        
        # 3. Retry Penalty: Deduct points based on retry attempts
        retry_penalty = self._calculate_retry_penalty(input_data)
        
        # 4. Edit Penalty: Reduce score for manual developer edits
        edit_penalty = self._calculate_edit_penalty(input_data)
        
        # 5. Complexity Handling: Adjust scoring based on task complexity
        complexity_handling = self._calculate_complexity_handling(input_data)
        
        # 6. Performance Impact: Measure before/after operation metrics
        performance_impact = self._calculate_performance_impact(input_data)
        
        # 7. Review Quality: Analyze PR review feedback and approval rates
        review_quality = self._calculate_review_quality(input_data, feedback_data)
        
        # 8. Developer Satisfaction: Incorporate manual feedback and ratings
        developer_satisfaction = self._calculate_developer_satisfaction(input_data, feedback_data)
        
        return DimensionalScores(
            clarity=clarity,
            coverage=coverage,
            retry_penalty=retry_penalty,
            edit_penalty=edit_penalty,
            complexity_handling=complexity_handling,
            performance_impact=performance_impact,
            review_quality=review_quality,
            developer_satisfaction=developer_satisfaction
        )
    
    def _calculate_clarity(self, input_data: ScoringInput) -> float:
        """Calculate clarity score based on template structure and completeness"""
        score = 1.0
        
        # Check if template name is well-formed
        if not input_data.template_name or len(input_data.template_name) < 5:
            score -= 0.2
        
        # Check if prompt hash is valid (indicates proper template processing)
        if not input_data.prompt_hash or len(input_data.prompt_hash) != 64:
            score -= 0.3
        
        # Check metadata completeness
        if not input_data.metadata:
            score -= 0.1
        
        # Bonus for structured task types
        if input_data.task_type in ['feature', 'bugfix', 'refactor']:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_coverage(self, input_data: ScoringInput) -> float:
        """Calculate coverage score based on file references and test inclusion"""
        score = 0.5  # Base score
        
        # File references boost
        if input_data.files_referenced:
            file_count = len(input_data.files_referenced)
            # Optimal range is 3-8 files
            if 3 <= file_count <= 8:
                score += 0.3
            elif file_count > 8:
                score += 0.2  # Too many files might indicate poor focus
            elif file_count > 0:
                score += 0.1  # Some files better than none
        
        # Test coverage boost
        if input_data.test_coverage > 0:
            score += min(0.3, input_data.test_coverage * 0.3)
        
        # Task-specific adjustments
        if input_data.task_type == 'test_generation':
            score += 0.2  # Bonus for test-focused tasks
        
        return max(0.0, min(1.0, score))
    
    def _calculate_retry_penalty(self, input_data: ScoringInput) -> float:
        """Calculate retry penalty - higher retry count = lower score"""
        if input_data.retry_count == 0:
            return 1.0
        
        # Exponential decay based on retry count
        penalty = math.exp(-input_data.retry_count * 0.5)
        return max(0.0, penalty)
    
    def _calculate_edit_penalty(self, input_data: ScoringInput) -> float:
        """Calculate edit penalty based on similarity to original"""
        if input_data.edit_similarity >= self.edit_penalty_threshold:
            return 1.0
        
        # Linear penalty below threshold
        penalty_factor = input_data.edit_similarity / self.edit_penalty_threshold
        return max(0.0, penalty_factor)
    
    def _calculate_complexity_handling(self, input_data: ScoringInput) -> float:
        """Calculate complexity handling score"""
        base_score = 0.5
        
        # Adjust based on complexity score
        complexity_factor = input_data.complexity_score
        
        # Higher complexity tasks that are handled well get bonus
        if complexity_factor > 0.7:
            base_score += 0.3
        elif complexity_factor > 0.5:
            base_score += 0.2
        else:
            base_score += 0.1
        
        # Adjust based on execution time (faster is better for complex tasks)
        if input_data.execution_time > 0:
            # Penalty for very long execution times
            if input_data.execution_time > 300:  # 5 minutes
                base_score -= 0.2
            elif input_data.execution_time > 120:  # 2 minutes
                base_score -= 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_performance_impact(self, input_data: ScoringInput) -> float:
        """Calculate performance impact score"""
        if input_data.perf_before == 0 and input_data.perf_after == 0:
            return 0.8  # Default score when no performance data
        
        if input_data.perf_before == 0:
            return 0.5  # No baseline to compare
        
        # Calculate improvement ratio
        improvement_ratio = input_data.perf_after / input_data.perf_before
        
        if improvement_ratio > 1.1:  # 10% improvement
            return 1.0
        elif improvement_ratio >= 0.9:  # Within 10% (acceptable)
            return 0.8
        elif improvement_ratio >= 0.8:  # 20% degradation
            return 0.6
        else:  # Significant degradation
            return 0.3
    
    def _calculate_review_quality(self, input_data: ScoringInput, feedback_data: List[FeedbackData] = None) -> float:
        """Calculate review quality score based on PR feedback"""
        if not feedback_data:
            return 0.7  # Default score when no feedback
        
        pr_feedback = [f for f in feedback_data if f.feedback_type == FeedbackType.PR_REVIEW]
        if not pr_feedback:
            return 0.7
        
        score = 0.5
        
        for feedback in pr_feedback:
            # PR approval boost
            if feedback.pr_approved:
                score += 0.3
            
            # Few review comments is good
            if feedback.review_comments is not None:
                if feedback.review_comments == 0:
                    score += 0.2
                elif feedback.review_comments <= 3:
                    score += 0.1
                else:
                    score -= 0.1
            
            # No changes requested is good
            if feedback.changes_requested is False:
                score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _calculate_developer_satisfaction(self, input_data: ScoringInput, feedback_data: List[FeedbackData] = None) -> float:
        """Calculate developer satisfaction score"""
        if not feedback_data:
            return 0.6  # Default score when no feedback
        
        satisfaction_feedback = [f for f in feedback_data if f.feedback_type == FeedbackType.DEVELOPER_SATISFACTION]
        if not satisfaction_feedback:
            return 0.6
        
        total_score = 0.0
        total_weight = 0.0
        
        for feedback in satisfaction_feedback:
            weight = 1.0
            
            # Direct satisfaction score
            if feedback.satisfaction_score is not None:
                total_score += feedback.satisfaction_score * weight
                total_weight += weight
            
            # Rating conversion (0-5 scale to 0-1 scale)
            elif feedback.rating is not None:
                normalized_rating = feedback.rating / 5.0
                total_score += normalized_rating * weight
                total_weight += weight
            
            # Recommendation boost
            if feedback.would_recommend:
                total_score += 0.2
                total_weight += 0.2
        
        if total_weight > 0:
            return max(0.0, min(1.0, total_score / total_weight))
        else:
            return 0.6
    
    def _calculate_penalties(self, input_data: ScoringInput) -> Dict[str, float]:
        """Calculate all penalties to be applied"""
        penalties = {}
        
        # Retry penalty
        if input_data.retry_count > 0:
            penalties['retry'] = input_data.retry_count * self.retry_penalty_factor
        
        # Edit similarity penalty
        if input_data.edit_similarity < self.edit_penalty_threshold:
            penalties['edit_similarity'] = self.edit_penalty_points
        
        # Performance penalty
        if input_data.perf_before > 0 and input_data.perf_after < input_data.perf_before:
            penalties['performance'] = self.performance_penalty_points
        
        return penalties
    
    def _calculate_bonuses(self, input_data: ScoringInput) -> Dict[str, float]:
        """Calculate all bonuses to be applied"""
        bonuses = {}
        
        # Complexity bonus
        if input_data.complexity_score > 0.7:
            bonuses['complexity'] = input_data.complexity_score * 10.0
        
        # Test coverage bonus
        if input_data.test_coverage > 0.8:
            bonuses['test_coverage'] = 5.0
        
        # Speed bonus for quick execution
        if input_data.execution_time > 0 and input_data.execution_time < 30:
            bonuses['speed'] = 3.0
        
        return bonuses
    
    def _calculate_adjustments(self, input_data: ScoringInput, dimensional_scores: DimensionalScores) -> Dict[str, float]:
        """Calculate adjustments based on dimensional scores"""
        adjustments = {}
        
        # Weighted dimensional adjustment
        dimensional_impact = (
            dimensional_scores.clarity * self.dimension_weights['clarity'] +
            dimensional_scores.coverage * self.dimension_weights['coverage'] +
            dimensional_scores.complexity_handling * self.dimension_weights['complexity_handling'] +
            dimensional_scores.performance_impact * self.dimension_weights['performance_impact'] +
            dimensional_scores.review_quality * self.dimension_weights['review_quality'] +
            dimensional_scores.developer_satisfaction * self.dimension_weights['developer_satisfaction']
        )
        
        # Penalty dimensions (inverted)
        penalty_impact = (
            (1.0 - dimensional_scores.retry_penalty) * self.dimension_weights['retry_penalty'] +
            (1.0 - dimensional_scores.edit_penalty) * self.dimension_weights['edit_penalty']
        )
        
        adjustments['dimensional_boost'] = dimensional_impact * 20.0  # Scale to points
        adjustments['penalty_reduction'] = -penalty_impact * 20.0  # Scale to points
        
        return adjustments
    
    def _calculate_final_score(self, base_score: float, dimensional_scores: DimensionalScores, 
                             penalties: Dict[str, float], bonuses: Dict[str, float], 
                             adjustments: Dict[str, float]) -> float:
        """Calculate the final score using the algorithm from requirements"""
        
        # Start with base score
        score = base_score
        
        # Apply penalties
        for penalty_name, penalty_value in penalties.items():
            score -= penalty_value
            logger.debug(f"Applied penalty {penalty_name}: -{penalty_value}")
        
        # Apply bonuses
        for bonus_name, bonus_value in bonuses.items():
            score += bonus_value
            logger.debug(f"Applied bonus {bonus_name}: +{bonus_value}")
        
        # Apply adjustments
        for adj_name, adj_value in adjustments.items():
            score += adj_value
            logger.debug(f"Applied adjustment {adj_name}: {adj_value:+.2f}")
        
        # Ensure score is within valid range
        final_score = max(0.0, min(100.0, score))
        
        logger.debug(f"Final score calculation: {base_score} -> {final_score}")
        return final_score
    
    def get_algorithm_info(self) -> Dict[str, str]:
        """Get information about the scoring algorithm"""
        return {
            'version': self.algorithm_version,
            'base_score': str(self.base_score),
            'dimension_weights': str(self.dimension_weights),
            'retry_penalty_factor': str(self.retry_penalty_factor),
            'edit_penalty_threshold': str(self.edit_penalty_threshold),
            'implementation_date': '2025-01-15'
        } 