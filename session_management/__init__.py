"""
Session Management Service Package

A standalone microservice for managing Jr Dev Agent session lifecycles.
"""

from .service import SessionManager, Session, SessionStatus, session_manager

__version__ = "1.0.0"
__all__ = ["SessionManager", "Session", "SessionStatus", "session_manager"] 