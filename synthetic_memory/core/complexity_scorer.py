import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import math

from .qdrant_client import QdrantVectorClient
from ..models.memory_models import ComplexityScoreResponse

logger = logging.getLogger(__name__)

class ComplexityScorer:
    """
    Complexity scorer for calculating task complexity based on multiple factors.
    
    Features:
    - Retry count analysis
    - Feature interdependency scoring
    - Lines of code impact assessment
    - Historical pattern analysis
    - Developer feedback integration
    - Normalized 0.0-1.0 scoring
    """
    
    def __init__(self, qdrant_client: QdrantVectorClient):
        self.qdrant_client = qdrant_client
        
        # Scoring weights
        self.weights = {
            "retry_factor": 0.25,
            "feature_complexity": 0.20,
            "loc_impact": 0.15,
            "historical_difficulty": 0.25,
            "dev_feedback": 0.15
        }
        
        logger.info("✅ ComplexityScorer initialized")
    
    async def calculate_complexity(
        self,
        ticket_id: str,
        retry_count: int = 0,
        features_referenced: List[str] = None,
        lines_of_code: int = 0,
        dev_feedback: Optional[Dict[str, Any]] = None,
        historical_context: Optional[Dict[str, Any]] = None
    ) -> ComplexityScoreResponse:
        """
        Calculate complexity score for a task.
        
        Args:
            ticket_id: Ticket identifier
            retry_count: Number of retry attempts
            features_referenced: List of features involved
            lines_of_code: Expected lines of code to modify
            dev_feedback: Developer feedback data
            historical_context: Historical context information
            
        Returns:
            ComplexityScoreResponse with score and analysis
        """
        try:
            start_time = datetime.utcnow()
            
            # Initialize score components
            score_components = {}
            factors = []
            recommendations = []
            
            # Calculate retry factor
            retry_score = self._calculate_retry_factor(retry_count)
            score_components["retry_factor"] = retry_score
            if retry_count > 0:
                factors.append(f"Retry attempts: {retry_count}")
                if retry_count > 2:
                    recommendations.append("High retry count - consider breaking into smaller tasks")
            
            # Calculate feature complexity
            feature_score = await self._calculate_feature_complexity(features_referenced or [])
            score_components["feature_complexity"] = feature_score
            if feature_score > 0.5:
                factors.append(f"Multiple features involved: {len(features_referenced or [])}")
                recommendations.append("Multi-feature task - plan for integration testing")
            
            # Calculate LOC impact
            loc_score = self._calculate_loc_impact(lines_of_code)
            score_components["loc_impact"] = loc_score
            if loc_score > 0.6:
                factors.append(f"High LOC impact: {lines_of_code}")
                recommendations.append("Large code changes - implement incrementally")
            
            # Calculate historical difficulty
            hist_score = await self._calculate_historical_difficulty(ticket_id, features_referenced or [])
            score_components["historical_difficulty"] = hist_score
            if hist_score > 0.7:
                factors.append("Similar tasks historically challenging")
                recommendations.append("Review historical patterns and common pitfalls")
            
            # Calculate developer feedback impact
            feedback_score = self._calculate_dev_feedback_impact(dev_feedback)
            score_components["dev_feedback"] = feedback_score
            if feedback_score > 0.5:
                factors.append("Previous developer feedback indicates complexity")
                recommendations.append("Consider pair programming or code review")
            
            # Calculate weighted final score
            final_score = sum(
                score_components[component] * self.weights[component]
                for component in score_components
            )
            
            # Normalize to 0.0-1.0 range
            final_score = max(0.0, min(1.0, final_score))
            
            # Add general recommendations based on final score
            if final_score > 0.8:
                recommendations.append("Very high complexity - consider architectural review")
            elif final_score > 0.6:
                recommendations.append("High complexity - plan additional testing")
            elif final_score > 0.4:
                recommendations.append("Medium complexity - standard development practices")
            else:
                recommendations.append("Low complexity - straightforward implementation")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(f"✅ Complexity calculated for ticket {ticket_id}: {final_score:.2f} in {processing_time:.2f}ms")
            
            return ComplexityScoreResponse(
                success=True,
                complexity_score=final_score,
                score_components=score_components,
                factors=factors,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"❌ Complexity calculation failed for ticket {ticket_id}: {e}")
            
            # Return fallback response
            return ComplexityScoreResponse(
                success=False,
                complexity_score=0.5,  # Default medium complexity
                score_components={},
                factors=["Error in complexity calculation"],
                recommendations=["Use standard development practices"]
            )
    
    def _calculate_retry_factor(self, retry_count: int) -> float:
        """
        Calculate complexity score based on retry count.
        
        Args:
            retry_count: Number of retry attempts
            
        Returns:
            Normalized score (0.0-1.0)
        """
        try:
            if retry_count == 0:
                return 0.0
            elif retry_count == 1:
                return 0.3
            elif retry_count == 2:
                return 0.6
            elif retry_count == 3:
                return 0.8
            else:
                return 1.0  # 4+ retries = maximum complexity
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate retry factor: {e}")
            return 0.5
    
    async def _calculate_feature_complexity(self, features_referenced: List[str]) -> float:
        """
        Calculate complexity score based on feature interdependencies.
        
        Args:
            features_referenced: List of features involved
            
        Returns:
            Normalized score (0.0-1.0)
        """
        try:
            if not features_referenced:
                return 0.0
            
            feature_count = len(features_referenced)
            
            # Base score based on feature count
            if feature_count == 1:
                base_score = 0.2
            elif feature_count == 2:
                base_score = 0.4
            elif feature_count == 3:
                base_score = 0.6
            elif feature_count == 4:
                base_score = 0.8
            else:
                base_score = 1.0
            
            # Analyze historical interdependencies
            interdependency_bonus = 0.0
            for feature in features_referenced:
                # Search for historical connections
                similar_memories = await self.qdrant_client.search(
                    query_vector=[0.0] * 768,  # Dummy vector for metadata search
                    limit=50,
                    score_threshold=0.0,
                    filter_conditions={"feature_id": feature}
                )
                
                # Count unique connected features
                connected_features = set()
                for memory in similar_memories:
                    connected_features.update(memory.payload.connected_features)
                
                # More connections = higher complexity
                if len(connected_features) > 3:
                    interdependency_bonus += 0.1
            
            final_score = min(1.0, base_score + interdependency_bonus)
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate feature complexity: {e}")
            return 0.5
    
    def _calculate_loc_impact(self, lines_of_code: int) -> float:
        """
        Calculate complexity score based on lines of code impact.
        
        Args:
            lines_of_code: Expected lines of code to modify
            
        Returns:
            Normalized score (0.0-1.0)
        """
        try:
            if lines_of_code <= 0:
                return 0.0
            
            # Logarithmic scaling for LOC impact
            # 1-50 lines: low complexity
            # 51-200 lines: medium complexity
            # 201-500 lines: high complexity
            # 500+ lines: very high complexity
            
            if lines_of_code <= 50:
                return 0.2
            elif lines_of_code <= 200:
                return 0.4
            elif lines_of_code <= 500:
                return 0.6
            elif lines_of_code <= 1000:
                return 0.8
            else:
                return 1.0
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate LOC impact: {e}")
            return 0.5
    
    async def _calculate_historical_difficulty(self, ticket_id: str, features_referenced: List[str]) -> float:
        """
        Calculate complexity score based on historical difficulty patterns.
        
        Args:
            ticket_id: Current ticket identifier
            features_referenced: List of features involved
            
        Returns:
            Normalized score (0.0-1.0)
        """
        try:
            if not features_referenced:
                return 0.0
            
            total_difficulty = 0.0
            feature_count = 0
            
            for feature in features_referenced:
                # Search for historical memories for this feature
                similar_memories = await self.qdrant_client.search(
                    query_vector=[0.0] * 768,  # Dummy vector for metadata search
                    limit=100,
                    score_threshold=0.0,
                    filter_conditions={"feature_id": feature}
                )
                
                if similar_memories:
                    # Calculate average difficulty indicators
                    retry_counts = [m.payload.retry_count for m in similar_memories]
                    complexity_scores = [m.payload.complexity_score for m in similar_memories]
                    
                    avg_retries = sum(retry_counts) / len(retry_counts)
                    avg_complexity = sum(complexity_scores) / len(complexity_scores)
                    
                    # Historical difficulty score for this feature
                    feature_difficulty = (avg_retries / 5.0) * 0.6 + avg_complexity * 0.4
                    total_difficulty += min(1.0, feature_difficulty)
                    feature_count += 1
            
            if feature_count == 0:
                return 0.0
            
            # Average difficulty across all features
            avg_difficulty = total_difficulty / feature_count
            return min(1.0, avg_difficulty)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate historical difficulty: {e}")
            return 0.5
    
    def _calculate_dev_feedback_impact(self, dev_feedback: Optional[Dict[str, Any]]) -> float:
        """
        Calculate complexity score based on developer feedback.
        
        Args:
            dev_feedback: Developer feedback data
            
        Returns:
            Normalized score (0.0-1.0)
        """
        try:
            if not dev_feedback:
                return 0.0
            
            # Analyze feedback components
            score = 0.0
            
            # Difficulty rating (1-5 scale)
            if "difficulty_rating" in dev_feedback:
                difficulty = dev_feedback["difficulty_rating"]
                score += (difficulty - 1) / 4.0 * 0.4  # Normalize to 0.0-0.4
            
            # Time estimate vs actual
            if "estimated_hours" in dev_feedback and "actual_hours" in dev_feedback:
                estimated = dev_feedback["estimated_hours"]
                actual = dev_feedback["actual_hours"]
                if estimated > 0:
                    time_ratio = actual / estimated
                    if time_ratio > 1.5:  # Took 50% longer than estimated
                        score += 0.3
                    elif time_ratio > 1.2:  # Took 20% longer
                        score += 0.2
            
            # Satisfaction rating (1-5 scale, inverted)
            if "satisfaction_rating" in dev_feedback:
                satisfaction = dev_feedback["satisfaction_rating"]
                dissatisfaction_score = (5 - satisfaction) / 4.0 * 0.3  # Normalize to 0.0-0.3
                score += dissatisfaction_score
            
            # Comments analysis (simplified)
            if "comments" in dev_feedback:
                comments = dev_feedback["comments"].lower()
                complexity_keywords = ["difficult", "complex", "challenging", "hard", "confusing", "tricky"]
                keyword_count = sum(1 for keyword in complexity_keywords if keyword in comments)
                score += min(0.2, keyword_count * 0.05)  # Max 0.2 from keywords
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate dev feedback impact: {e}")
            return 0.0
    
    async def get_complexity_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about complexity scoring.
        
        Returns:
            Dictionary with complexity statistics
        """
        try:
            # Get all memory points for analysis
            all_memories = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata search
                limit=10000,
                score_threshold=0.0
            )
            
            if not all_memories:
                return {"message": "No complexity data available"}
            
            # Analyze complexity distribution
            complexity_scores = [m.payload.complexity_score for m in all_memories]
            retry_counts = [m.payload.retry_count for m in all_memories]
            
            # Calculate statistics
            avg_complexity = sum(complexity_scores) / len(complexity_scores)
            max_complexity = max(complexity_scores)
            min_complexity = min(complexity_scores)
            
            avg_retries = sum(retry_counts) / len(retry_counts)
            max_retries = max(retry_counts)
            
            # Distribution analysis
            low_complexity = len([s for s in complexity_scores if s < 0.4])
            medium_complexity = len([s for s in complexity_scores if 0.4 <= s < 0.7])
            high_complexity = len([s for s in complexity_scores if s >= 0.7])
            
            stats = {
                "total_scored_tasks": len(all_memories),
                "complexity_distribution": {
                    "low": low_complexity,
                    "medium": medium_complexity,
                    "high": high_complexity
                },
                "average_complexity": round(avg_complexity, 3),
                "max_complexity": round(max_complexity, 3),
                "min_complexity": round(min_complexity, 3),
                "average_retries": round(avg_retries, 2),
                "max_retries": max_retries,
                "scoring_weights": self.weights
            }
            
            logger.info(f"✅ Generated complexity statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get complexity statistics: {e}")
            return {"error": str(e)}
    
    async def analyze_complexity_trends(self, feature_id: str) -> Dict[str, Any]:
        """
        Analyze complexity trends for a specific feature.
        
        Args:
            feature_id: Feature identifier
            
        Returns:
            Dictionary with trend analysis
        """
        try:
            # Get historical data for this feature
            feature_memories = await self.qdrant_client.search(
                query_vector=[0.0] * 768,  # Dummy vector for metadata search
                limit=100,
                score_threshold=0.0,
                filter_conditions={"feature_id": feature_id}
            )
            
            if not feature_memories:
                return {"message": f"No historical data for feature {feature_id}"}
            
            # Sort by creation time (assuming payload has created_at)
            sorted_memories = sorted(feature_memories, key=lambda m: m.payload.created_at)
            
            # Calculate trends
            complexity_trend = [m.payload.complexity_score for m in sorted_memories]
            retry_trend = [m.payload.retry_count for m in sorted_memories]
            
            # Calculate trend direction
            if len(complexity_trend) >= 2:
                recent_avg = sum(complexity_trend[-5:]) / min(5, len(complexity_trend))
                early_avg = sum(complexity_trend[:5]) / min(5, len(complexity_trend))
                trend_direction = "increasing" if recent_avg > early_avg else "decreasing"
            else:
                trend_direction = "stable"
            
            trends = {
                "feature_id": feature_id,
                "total_tasks": len(feature_memories),
                "complexity_trend": trend_direction,
                "average_complexity": round(sum(complexity_trend) / len(complexity_trend), 3),
                "average_retries": round(sum(retry_trend) / len(retry_trend), 2),
                "recent_complexity": round(sum(complexity_trend[-5:]) / min(5, len(complexity_trend)), 3),
                "complexity_history": complexity_trend[-10:]  # Last 10 values
            }
            
            logger.info(f"✅ Analyzed complexity trends for feature {feature_id}")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze complexity trends: {e}")
            return {"error": str(e)} 