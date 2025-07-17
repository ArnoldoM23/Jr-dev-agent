"""
Session Management Service Client

HTTP client for communicating with the Session Management microservice.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
import os


class SessionManagementClient:
    """Client for the Session Management microservice"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("SESSION_MANAGEMENT_URL", "http://localhost:8003")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)
    
    async def create_session(self, ticket_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session
        
        Args:
            ticket_id: The Jira ticket ID
            metadata: Additional metadata for the session
            
        Returns:
            session_id: The created session ID
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/sessions",
                json={
                    "ticket_id": ticket_id,
                    "metadata": metadata
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result["session_id"]
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error creating session: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID
        
        Args:
            session_id: The session ID
            
        Returns:
            Session data or None if not found
        """
        try:
            response = await self.client.get(f"{self.base_url}/sessions/{session_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            self.logger.error(f"HTTP error getting session: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting session: {e}")
            raise
    
    async def update_session(self, session_id: str, **updates) -> bool:
        """
        Update a session
        
        Args:
            session_id: The session ID
            **updates: Fields to update
            
        Returns:
            True if successful, False if not found
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/sessions/{session_id}",
                json=updates
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return False
            self.logger.error(f"HTTP error updating session: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating session: {e}")
            raise
    
    async def complete_session(self, session_id: str, pr_url: Optional[str] = None) -> bool:
        """
        Mark a session as completed
        
        Args:
            session_id: The session ID
            pr_url: Optional PR URL
            
        Returns:
            True if successful, False if not found
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/sessions/{session_id}/complete",
                json={
                    "pr_url": pr_url
                }
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return False
            self.logger.error(f"HTTP error completing session: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error completing session: {e}")
            raise
    
    async def fail_session(self, session_id: str, error_message: str) -> bool:
        """
        Mark a session as failed
        
        Args:
            session_id: The session ID
            error_message: Error message
            
        Returns:
            True if successful, False if not found
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/sessions/{session_id}/fail",
                json={
                    "error_message": error_message
                }
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return False
            self.logger.error(f"HTTP error failing session: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error failing session: {e}")
            raise
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of the Session Management service"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting Session Management health: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
session_management_client = SessionManagementClient() 