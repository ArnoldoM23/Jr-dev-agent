"""
PESS Result Emitter

Stage 5 of the 5-stage pipeline: Emits results to database and downstream systems.
Handles database persistence and external system notifications.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import asyncio
from sqlalchemy.orm import Session

from ..models.scoring_models import ScoringOutput, ScoringStage
from ..models.database_models import (
    ScoreRecord, SessionRecord, TemplateRecord, 
    get_recent_scores, get_template_performance
)

logger = logging.getLogger(__name__)

class ResultEmitter:
    """
    Emitter component for persisting results and notifying downstream systems
    """
    
    def __init__(self, db_session: Session = None):
        self.emitter_stage = ScoringStage.EMITTER
        self.db_session = db_session
        
        # Emission tracking
        self.emission_stats = {
            'total_emissions': 0,
            'successful_emissions': 0,
            'failed_emissions': 0,
            'last_emission': None,
            'downstream_notifications': 0
        }
        
        # Downstream system configurations
        self.downstream_systems = {
            'langraph_mcp': {'enabled': True, 'url': 'http://langraph-mcp:8000'},
            'promptbuilder': {'enabled': True, 'url': 'http://promptbuilder:8001'},
            'analytics_dashboard': {'enabled': True, 'url': 'http://analytics:8080'}
        }
        
        logger.info("ResultEmitter initialized")
    
    def emit_result(self, scoring_output: ScoringOutput) -> Dict[str, Any]:
        """
        Emit scoring result to database and downstream systems
        
        Args:
            scoring_output: Versioned scoring output to emit
            
        Returns:
            Emission result summary
        """
        logger.debug(f"Emitting result for session {scoring_output.session_id}")
        
        emission_result = {
            'session_id': scoring_output.session_id,
            'database_saved': False,
            'downstream_notifications': [],
            'errors': []
        }
        
        try:
            # Update pipeline stage
            scoring_output.pipeline_stage = self.emitter_stage
            
            # Emit to database
            if self.db_session:
                database_result = self._emit_to_database(scoring_output)
                emission_result['database_saved'] = database_result['success']
                if not database_result['success']:
                    emission_result['errors'].append(database_result['error'])
            
            # Emit to downstream systems
            downstream_results = self._emit_to_downstream_systems(scoring_output)
            emission_result['downstream_notifications'] = downstream_results
            
            # Update emission statistics
            self._update_emission_stats(success=True)
            
            logger.info(f"Result emission completed for session {scoring_output.session_id}")
            
            return emission_result
            
        except Exception as e:
            logger.error(f"Failed to emit result for session {scoring_output.session_id}: {str(e)}")
            emission_result['errors'].append(str(e))
            self._update_emission_stats(success=False)
            return emission_result
    
    def _emit_to_database(self, scoring_output: ScoringOutput) -> Dict[str, Any]:
        """Emit scoring result to database"""
        
        try:
            # Create score record
            score_record = ScoreRecord(
                scoring_id=scoring_output.scoring_id,
                session_id=scoring_output.session_id,
                ticket_id=scoring_output.template_correlation.get('ticket_id', ''),
                task_type=scoring_output.template_correlation.get('task_type', ''),
                template_name=scoring_output.template_correlation.get('template_name', ''),
                template_version=scoring_output.template_correlation.get('template_version', ''),
                prompt_hash=scoring_output.template_correlation.get('prompt_hash', ''),
                
                # Scoring results
                base_score=scoring_output.metrics.base_score,
                final_score=scoring_output.metrics.final_score,
                dimensional_scores=scoring_output.metrics.dimensional_scores.dict(),
                adjustments=scoring_output.metrics.adjustments,
                penalties=scoring_output.metrics.penalties,
                bonuses=scoring_output.metrics.bonuses,
                
                # Pipeline metadata
                pipeline_stage=scoring_output.pipeline_stage.value,
                processing_time=scoring_output.processing_time,
                score_version=scoring_output.score_version,
                
                # Quality indicators
                confidence_score=scoring_output.confidence_score,
                data_quality=scoring_output.data_quality,
                
                # Additional data
                template_correlation=scoring_output.template_correlation,
                recommendations=scoring_output.recommendations,
                alerts=scoring_output.alerts,
                
                # Timestamps
                created_at=scoring_output.timestamp,
                updated_at=datetime.utcnow()
            )
            
            # Save to database
            self.db_session.add(score_record)
            self.db_session.commit()
            
            # Update session record
            self._update_session_record(scoring_output)
            
            # Update template record
            self._update_template_record(scoring_output)
            
            logger.debug(f"Score record saved to database for session {scoring_output.session_id}")
            
            return {'success': True, 'record_id': str(score_record.id)}
            
        except Exception as e:
            logger.error(f"Database emission failed: {str(e)}")
            self.db_session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _update_session_record(self, scoring_output: ScoringOutput) -> None:
        """Update or create session record"""
        
        session_record = self.db_session.query(SessionRecord).filter_by(
            session_id=scoring_output.session_id
        ).first()
        
        if session_record:
            # Update existing session
            session_record.total_scores += 1
            session_record.average_score = (
                (session_record.average_score * (session_record.total_scores - 1) + 
                 scoring_output.metrics.final_score) / session_record.total_scores
            )
            session_record.best_score = max(session_record.best_score, scoring_output.metrics.final_score)
            session_record.worst_score = min(session_record.worst_score, scoring_output.metrics.final_score)
            session_record.updated_at = datetime.utcnow()
        else:
            # Create new session record
            session_record = SessionRecord(
                session_id=scoring_output.session_id,
                ticket_id=scoring_output.template_correlation.get('ticket_id', ''),
                task_type=scoring_output.template_correlation.get('task_type', ''),
                template_name=scoring_output.template_correlation.get('template_name', ''),
                template_version=scoring_output.template_correlation.get('template_version', ''),
                total_scores=1,
                best_score=scoring_output.metrics.final_score,
                worst_score=scoring_output.metrics.final_score,
                average_score=scoring_output.metrics.final_score
            )
            self.db_session.add(session_record)
        
        self.db_session.commit()
    
    def _update_template_record(self, scoring_output: ScoringOutput) -> None:
        """Update or create template performance record"""
        
        template_name = scoring_output.template_correlation.get('template_name', '')
        template_version = scoring_output.template_correlation.get('template_version', '')
        
        template_record = self.db_session.query(TemplateRecord).filter_by(
            template_name=template_name,
            template_version=template_version
        ).first()
        
        if template_record:
            # Update existing template record
            template_record.usage_count += 1
            template_record.average_score = (
                (template_record.average_score * (template_record.usage_count - 1) + 
                 scoring_output.metrics.final_score) / template_record.usage_count
            )
            
            # Update dimensional averages
            dimensional_scores = scoring_output.metrics.dimensional_scores.dict()
            current_averages = template_record.dimensional_averages or {}
            
            for dimension, score in dimensional_scores.items():
                if dimension in current_averages:
                    current_averages[dimension] = (
                        (current_averages[dimension] * (template_record.usage_count - 1) + score) / 
                        template_record.usage_count
                    )
                else:
                    current_averages[dimension] = score
            
            template_record.dimensional_averages = current_averages
            template_record.updated_at = datetime.utcnow()
            template_record.last_calculated = datetime.utcnow()
            
        else:
            # Create new template record
            template_record = TemplateRecord(
                template_name=template_name,
                template_version=template_version,
                usage_count=1,
                average_score=scoring_output.metrics.final_score,
                dimensional_averages=scoring_output.metrics.dimensional_scores.dict()
            )
            self.db_session.add(template_record)
        
        self.db_session.commit()
    
    def _emit_to_downstream_systems(self, scoring_output: ScoringOutput) -> List[Dict[str, Any]]:
        """Emit results to downstream systems"""
        
        downstream_results = []
        
        # Prepare notification payload
        notification_payload = {
            'session_id': scoring_output.session_id,
            'scoring_id': scoring_output.scoring_id,
            'final_score': scoring_output.metrics.final_score,
            'dimensional_scores': scoring_output.metrics.dimensional_scores.dict(),
            'template_info': {
                'name': scoring_output.template_correlation.get('template_name'),
                'version': scoring_output.template_correlation.get('template_version')
            },
            'alerts': scoring_output.alerts,
            'recommendations': scoring_output.recommendations,
            'timestamp': scoring_output.timestamp.isoformat()
        }
        
        # Emit to each configured downstream system
        for system_name, config in self.downstream_systems.items():
            if config.get('enabled', False):
                try:
                    result = self._notify_downstream_system(system_name, config, notification_payload)
                    downstream_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to notify {system_name}: {str(e)}")
                    downstream_results.append({
                        'system': system_name,
                        'success': False,
                        'error': str(e)
                    })
        
        return downstream_results
    
    def _notify_downstream_system(self, system_name: str, config: Dict[str, Any], 
                                 payload: Dict[str, Any]) -> Dict[str, Any]:
        """Notify a specific downstream system"""
        
        # This is a simplified implementation
        # In a real system, you would use HTTP requests or message queues
        
        logger.info(f"Notifying {system_name} with scoring result")
        
        # System-specific payload modifications
        if system_name == 'langraph_mcp':
            # LangGraph MCP needs specific format
            mcp_payload = {
                'event_type': 'scoring_completed',
                'session_id': payload['session_id'],
                'score_data': payload
            }
            # Here you would send HTTP POST to LangGraph MCP
            
        elif system_name == 'promptbuilder':
            # PromptBuilder needs template feedback
            pb_payload = {
                'template_feedback': {
                    'template_name': payload['template_info']['name'],
                    'score': payload['final_score'],
                    'recommendations': payload['recommendations']
                }
            }
            # Here you would send HTTP POST to PromptBuilder
            
        elif system_name == 'analytics_dashboard':
            # Analytics dashboard needs aggregated data
            analytics_payload = {
                'metrics_update': {
                    'session_id': payload['session_id'],
                    'score': payload['final_score'],
                    'dimensional_scores': payload['dimensional_scores']
                }
            }
            # Here you would send HTTP POST to Analytics Dashboard
        
        # Update notification statistics
        self.emission_stats['downstream_notifications'] += 1
        
        return {
            'system': system_name,
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def batch_emit(self, scoring_outputs: List[ScoringOutput]) -> List[Dict[str, Any]]:
        """
        Batch emit multiple scoring outputs
        
        Args:
            scoring_outputs: List of scoring outputs to emit
            
        Returns:
            List of emission results
        """
        logger.info(f"Batch emitting {len(scoring_outputs)} outputs")
        
        emission_results = []
        
        for scoring_output in scoring_outputs:
            try:
                result = self.emit_result(scoring_output)
                emission_results.append(result)
            except Exception as e:
                logger.error(f"Failed to emit session {scoring_output.session_id}: {str(e)}")
                emission_results.append({
                    'session_id': scoring_output.session_id,
                    'database_saved': False,
                    'downstream_notifications': [],
                    'errors': [str(e)]
                })
        
        logger.info(f"Batch emission completed for {len(emission_results)} outputs")
        return emission_results
    
    def _update_emission_stats(self, success: bool) -> None:
        """Update emission statistics"""
        
        self.emission_stats['total_emissions'] += 1
        self.emission_stats['last_emission'] = datetime.utcnow().isoformat()
        
        if success:
            self.emission_stats['successful_emissions'] += 1
        else:
            self.emission_stats['failed_emissions'] += 1
    
    def configure_downstream_system(self, system_name: str, config: Dict[str, Any]) -> None:
        """Configure a downstream system"""
        
        self.downstream_systems[system_name] = config
        logger.info(f"Configured downstream system: {system_name}")
    
    def get_emission_stats(self) -> Dict[str, Any]:
        """Get emission statistics"""
        
        stats = dict(self.emission_stats)
        
        # Calculate success rate
        total = stats['total_emissions']
        if total > 0:
            stats['success_rate'] = stats['successful_emissions'] / total
            stats['failure_rate'] = stats['failed_emissions'] / total
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        stats['downstream_systems'] = self.downstream_systems
        stats['emitter_stage'] = self.emitter_stage.value
        
        return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        if not self.db_session:
            return {'error': 'No database session available'}
        
        try:
            # Get recent scores
            recent_scores = get_recent_scores(self.db_session, days=30, limit=10)
            
            # Get template performance
            template_performance = get_template_performance(self.db_session, days=30)
            
            return {
                'recent_scores_count': len(recent_scores),
                'template_performance_count': len(template_performance),
                'database_connection': 'active',
                'last_query': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'database_connection': 'failed'
            } 