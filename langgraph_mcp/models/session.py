"""
Session Management

This module handles session tracking and management for Jr Dev Agent workflows.
Sessions track the lifecycle of a ticket from initial request to PR completion.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import uuid4
from dataclasses import dataclass, asdict
from enum import Enum


class SessionStatus(Enum):
    """Session status enumeration"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class Session:
    """
    Session data class
    
    Represents a single Jr Dev Agent session from ticket to PR completion.
    """
    session_id: str
    ticket_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    # Optional fields
    prompt_generated: Optional[str] = None
    prompt_hash: Optional[str] = None
    template_used: Optional[str] = None
    pr_url: Optional[str] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, SessionStatus):
                result[key] = value.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary"""
        # Convert string timestamps back to datetime objects
        for key in ['created_at', 'updated_at', 'completed_at']:
            if key in data and data[key] is not None:
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert status string to enum
        if 'status' in data:
            data['status'] = SessionStatus(data['status'])
        
        return cls(**data)


class SessionManager:
    """
    Session Manager
    
    Manages Jr Dev Agent sessions including creation, tracking, and cleanup.
    In a production environment, this would be backed by a database.
    """
    
    def __init__(self, session_timeout_minutes: int = 60):
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
    def initialize(self):
        """Initialize the session manager"""
        self.logger.info("SessionManager initialized")
    
    def create_session(self, ticket_id: str, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new session
        
        Args:
            ticket_id: The Jira ticket ID
            metadata: Additional metadata for the session
            
        Returns:
            session_id: The created session ID
        """
        session_id = f"jr_dev_{ticket_id}_{str(uuid4())[:8]}"
        
        session = Session(
            session_id=session_id,
            ticket_id=ticket_id,
            status=SessionStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"Created session: {session_id} for ticket: {ticket_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID
        
        Args:
            session_id: The session ID
            
        Returns:
            Session object or None if not found
        """
        session = self.sessions.get(session_id)
        
        if session:
            # Check if session has expired
            if self._is_session_expired(session):
                self.expire_session(session_id)
                return None
        
        return session
    
    def update_session(self, session_id: str, **updates) -> bool:
        """
        Update a session with new data
        
        Args:
            session_id: The session ID
            **updates: Fields to update
            
        Returns:
            True if session was updated, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Update allowed fields
        allowed_fields = [
            'status', 'prompt_generated', 'prompt_hash', 'template_used',
            'pr_url', 'completed_at', 'error_message', 'metadata'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(session, field, value)
        
        session.updated_at = datetime.now()
        self.logger.info(f"Updated session: {session_id}")
        
        return True
    
    def complete_session(self, session_id: str, pr_url: Optional[str] = None, 
                        completed_at: Optional[str] = None) -> bool:
        """
        Mark a session as completed
        
        Args:
            session_id: The session ID
            pr_url: Optional PR URL
            completed_at: Optional completion timestamp (ISO format)
            
        Returns:
            True if session was completed, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.COMPLETED
        session.pr_url = pr_url
        session.completed_at = datetime.fromisoformat(completed_at) if completed_at else datetime.now()
        session.updated_at = datetime.now()
        
        self.logger.info(f"Completed session: {session_id}")
        return True
    
    def fail_session(self, session_id: str, error_message: str) -> bool:
        """
        Mark a session as failed
        
        Args:
            session_id: The session ID
            error_message: Error message
            
        Returns:
            True if session was failed, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.FAILED
        session.error_message = error_message
        session.updated_at = datetime.now()
        
        self.logger.info(f"Failed session: {session_id} - {error_message}")
        return True
    
    def expire_session(self, session_id: str) -> bool:
        """
        Mark a session as expired
        
        Args:
            session_id: The session ID
            
        Returns:
            True if session was expired, False if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.EXPIRED
        session.updated_at = datetime.now()
        
        self.logger.info(f"Expired session: {session_id}")
        return True
    
    def get_sessions_by_ticket(self, ticket_id: str) -> List[Session]:
        """
        Get all sessions for a specific ticket
        
        Args:
            ticket_id: The ticket ID
            
        Returns:
            List of sessions for the ticket
        """
        return [session for session in self.sessions.values() 
                if session.ticket_id == ticket_id]
    
    def get_active_sessions(self) -> List[Session]:
        """
        Get all active (non-completed, non-failed, non-expired) sessions
        
        Returns:
            List of active sessions
        """
        active_statuses = [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]
        active_sessions = []
        
        for session in self.sessions.values():
            if session.status in active_statuses:
                if not self._is_session_expired(session):
                    active_sessions.append(session)
                else:
                    self.expire_session(session.session_id)
        
        return active_sessions
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions as dictionaries
        
        Returns:
            List of session dictionaries
        """
        return [session.to_dict() for session in self.sessions.values()]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        expired_count = 0
        current_time = datetime.now()
        
        for session_id, session in list(self.sessions.items()):
            if self._is_session_expired(session):
                self.expire_session(session_id)
                expired_count += 1
        
        if expired_count > 0:
            self.logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return expired_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics
        
        Returns:
            Dictionary of session statistics
        """
        status_counts = {}
        for status in SessionStatus:
            status_counts[status.value] = 0
        
        for session in self.sessions.values():
            status_counts[session.status.value] += 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(self.get_active_sessions()),
            "status_breakdown": status_counts,
            "session_timeout_minutes": self.session_timeout.total_seconds() / 60
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("SessionManager cleanup complete")
    
    def _is_session_expired(self, session: Session) -> bool:
        """
        Check if a session has expired
        
        Args:
            session: The session to check
            
        Returns:
            True if session is expired
        """
        if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
            return False
        
        return datetime.now() - session.updated_at > self.session_timeout
    
    def export_sessions(self, filename: str):
        """
        Export sessions to JSON file
        
        Args:
            filename: Output filename
        """
        sessions_data = [session.to_dict() for session in self.sessions.values()]
        
        with open(filename, 'w') as f:
            json.dump(sessions_data, f, indent=2)
        
        self.logger.info(f"Exported {len(sessions_data)} sessions to {filename}")
    
    def import_sessions(self, filename: str):
        """
        Import sessions from JSON file
        
        Args:
            filename: Input filename
        """
        with open(filename, 'r') as f:
            sessions_data = json.load(f)
        
        for session_data in sessions_data:
            session = Session.from_dict(session_data)
            self.sessions[session.session_id] = session
        
        self.logger.info(f"Imported {len(sessions_data)} sessions from {filename}") 