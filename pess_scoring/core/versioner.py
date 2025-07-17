"""
PESS Score Versioner

Stage 4 of the 5-stage pipeline: Versions all scores with template and hash correlation.
Manages score versioning and template correlation tracking.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib

from ..models.scoring_models import ScoringOutput, ScoringStage

logger = logging.getLogger(__name__)

class ScoreVersioner:
    """
    Versioner component for managing score versions and template correlation
    """
    
    def __init__(self):
        self.versioning_stage = ScoringStage.VERSIONER
        self.version_format = "v{major}.{minor}.{patch}"
        self.current_version = {"major": 1, "minor": 0, "patch": 0}
        
        # Version tracking
        self.version_history = {}
        self.template_versions = {}
        
        logger.info("ScoreVersioner initialized")
    
    def version_score(self, scoring_output: ScoringOutput) -> ScoringOutput:
        """
        Version the scoring output with template and hash correlation
        
        Args:
            scoring_output: Scoring output to version
            
        Returns:
            Versioned scoring output
        """
        logger.debug(f"Versioning score for session {scoring_output.session_id}")
        
        # Create versioned copy
        versioned_output = ScoringOutput(**scoring_output.dict())
        
        # Update pipeline stage
        versioned_output.pipeline_stage = self.versioning_stage
        
        # Generate version information
        version_info = self._generate_version_info(scoring_output)
        versioned_output.score_version = version_info['version']
        
        # Update template correlation with versioning info
        versioned_output.template_correlation.update({
            'scoring_version': version_info['version'],
            'version_hash': version_info['hash'],
            'versioning_timestamp': datetime.utcnow().isoformat(),
            'version_metadata': version_info['metadata']
        })
        
        # Track version history
        self._track_version_history(versioned_output, version_info)
        
        logger.info(f"Score versioned for session {scoring_output.session_id}, "
                   f"version: {version_info['version']}")
        
        return versioned_output
    
    def _generate_version_info(self, scoring_output: ScoringOutput) -> Dict[str, Any]:
        """Generate comprehensive version information"""
        
        # Get template information
        template_name = scoring_output.template_correlation.get('template_name', 'unknown')
        template_version = scoring_output.template_correlation.get('template_version', '1.0')
        prompt_hash = scoring_output.template_correlation.get('prompt_hash', '')
        
        # Generate version string
        version_string = self.version_format.format(**self.current_version)
        
        # Create version-specific hash
        version_content = f"{version_string}:{template_name}:{template_version}:{prompt_hash}"
        version_hash = hashlib.sha256(version_content.encode()).hexdigest()[:16]
        
        # Create version metadata
        version_metadata = {
            'algorithm_version': scoring_output.score_version,
            'template_info': {
                'name': template_name,
                'version': template_version,
                'hash': prompt_hash
            },
            'scoring_metrics': {
                'final_score': scoring_output.metrics.final_score,
                'confidence_score': scoring_output.confidence_score,
                'data_quality': scoring_output.data_quality
            },
            'processing_info': {
                'processing_time': scoring_output.processing_time,
                'timestamp': scoring_output.timestamp.isoformat()
            }
        }
        
        return {
            'version': version_string,
            'hash': version_hash,
            'metadata': version_metadata
        }
    
    def _track_version_history(self, scoring_output: ScoringOutput, 
                             version_info: Dict[str, Any]) -> None:
        """Track version history for analytics"""
        
        session_id = scoring_output.session_id
        version = version_info['version']
        
        # Track per-session versions
        if session_id not in self.version_history:
            self.version_history[session_id] = []
        
        self.version_history[session_id].append({
            'version': version,
            'hash': version_info['hash'],
            'timestamp': datetime.utcnow().isoformat(),
            'final_score': scoring_output.metrics.final_score,
            'template_name': scoring_output.template_correlation.get('template_name')
        })
        
        # Track template versions
        template_name = scoring_output.template_correlation.get('template_name')
        if template_name:
            if template_name not in self.template_versions:
                self.template_versions[template_name] = []
            
            self.template_versions[template_name].append({
                'session_id': session_id,
                'version': version,
                'score': scoring_output.metrics.final_score,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def batch_version(self, scoring_outputs: List[ScoringOutput]) -> List[ScoringOutput]:
        """
        Batch version multiple scoring outputs
        
        Args:
            scoring_outputs: List of scoring outputs to version
            
        Returns:
            List of versioned scoring outputs
        """
        logger.info(f"Batch versioning {len(scoring_outputs)} outputs")
        
        versioned_outputs = []
        
        for scoring_output in scoring_outputs:
            try:
                versioned_output = self.version_score(scoring_output)
                versioned_outputs.append(versioned_output)
            except Exception as e:
                logger.error(f"Failed to version session {scoring_output.session_id}: {str(e)}")
                # Add error information to original output
                error_output = ScoringOutput(**scoring_output.dict())
                error_output.pipeline_stage = self.versioning_stage
                error_output.alerts.append(f"Versioning failed: {str(e)}")
                versioned_outputs.append(error_output)
        
        logger.info(f"Batch versioning completed for {len(versioned_outputs)} outputs")
        return versioned_outputs
    
    def get_version_history(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get version history for a session or all sessions
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Version history data
        """
        if session_id:
            return {
                'session_id': session_id,
                'versions': self.version_history.get(session_id, [])
            }
        else:
            return {
                'total_sessions': len(self.version_history),
                'all_versions': self.version_history
            }
    
    def get_template_version_analytics(self, template_name: str = None) -> Dict[str, Any]:
        """
        Get version analytics for templates
        
        Args:
            template_name: Optional template name to filter by
            
        Returns:
            Template version analytics
        """
        if template_name:
            template_data = self.template_versions.get(template_name, [])
            if template_data:
                scores = [item['score'] for item in template_data]
                return {
                    'template_name': template_name,
                    'version_count': len(template_data),
                    'avg_score': sum(scores) / len(scores),
                    'min_score': min(scores),
                    'max_score': max(scores),
                    'versions': template_data
                }
            else:
                return {
                    'template_name': template_name,
                    'version_count': 0,
                    'versions': []
                }
        else:
            # Return analytics for all templates
            analytics = {}
            for template_name, template_data in self.template_versions.items():
                scores = [item['score'] for item in template_data]
                analytics[template_name] = {
                    'version_count': len(template_data),
                    'avg_score': sum(scores) / len(scores),
                    'min_score': min(scores),
                    'max_score': max(scores),
                    'last_updated': max(item['timestamp'] for item in template_data)
                }
            
            return {
                'total_templates': len(analytics),
                'template_analytics': analytics
            }
    
    def increment_version(self, increment_type: str = 'patch') -> str:
        """
        Increment the version number
        
        Args:
            increment_type: Type of increment ('major', 'minor', 'patch')
            
        Returns:
            New version string
        """
        if increment_type == 'major':
            self.current_version['major'] += 1
            self.current_version['minor'] = 0
            self.current_version['patch'] = 0
        elif increment_type == 'minor':
            self.current_version['minor'] += 1
            self.current_version['patch'] = 0
        elif increment_type == 'patch':
            self.current_version['patch'] += 1
        else:
            raise ValueError(f"Invalid increment type: {increment_type}")
        
        new_version = self.version_format.format(**self.current_version)
        logger.info(f"Version incremented to {new_version}")
        return new_version
    
    def correlate_templates(self, template_name: str, 
                          score_threshold: float = 80.0) -> Dict[str, Any]:
        """
        Find correlations between templates and scores
        
        Args:
            template_name: Template to analyze
            score_threshold: Minimum score threshold for analysis
            
        Returns:
            Template correlation analysis
        """
        template_data = self.template_versions.get(template_name, [])
        
        if not template_data:
            return {
                'template_name': template_name,
                'correlation_analysis': 'No data available'
            }
        
        # Filter by score threshold
        high_scoring = [item for item in template_data if item['score'] >= score_threshold]
        low_scoring = [item for item in template_data if item['score'] < score_threshold]
        
        analysis = {
            'template_name': template_name,
            'total_versions': len(template_data),
            'high_scoring_count': len(high_scoring),
            'low_scoring_count': len(low_scoring),
            'success_rate': len(high_scoring) / len(template_data) if template_data else 0,
            'score_threshold': score_threshold
        }
        
        if high_scoring:
            high_scores = [item['score'] for item in high_scoring]
            analysis['high_scoring_stats'] = {
                'avg_score': sum(high_scores) / len(high_scores),
                'min_score': min(high_scores),
                'max_score': max(high_scores)
            }
        
        if low_scoring:
            low_scores = [item['score'] for item in low_scoring]
            analysis['low_scoring_stats'] = {
                'avg_score': sum(low_scores) / len(low_scores),
                'min_score': min(low_scores),
                'max_score': max(low_scores)
            }
        
        return analysis
    
    def get_versioning_stats(self) -> Dict[str, Any]:
        """Get versioning statistics"""
        return {
            'current_version': self.version_format.format(**self.current_version),
            'version_components': self.current_version,
            'total_sessions_versioned': len(self.version_history),
            'total_templates_tracked': len(self.template_versions),
            'versioning_stage': self.versioning_stage.value,
            'version_format': self.version_format,
            'last_updated': datetime.utcnow().isoformat()
        } 