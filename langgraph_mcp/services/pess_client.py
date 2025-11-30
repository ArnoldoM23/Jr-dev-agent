"""
PESS Client Service for Jr Dev Agent

This service provides integration with PESS (Prompt Effectiveness Scoring System)
for continuous improvement of prompt quality and template optimization.
"""

import httpx
import logging
import os
import time
from typing import Dict, Any, Optional


class PESSClient:
    """
    PESS Client Service for scoring and analytics
    
    This service integrates with the PESS system to provide prompt effectiveness
    scoring and recommendations for template optimization.
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize PESS client service.
        
        Args:
            base_url: PESS API base URL (defaults to env var or config)
        """
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url or os.getenv("PESS_URL")
        self.api_key = os.getenv("PESS_API_KEY")
        self.initialized = False
    
    async def initialize(self):
        """Initialize the PESS client service"""
        self.logger.info("Initializing PESS Client...")
        
        # Load config if available
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
                pess_config = config.get("pess", {})
                if "url" in pess_config:
                    self.base_url = pess_config["url"]
                if "token" in pess_config:
                    self.api_key = pess_config["token"]
        except FileNotFoundError:
            pass  # Use environment variables
        
        self.initialized = True
        status = "configured" if self.base_url else "mock mode"
        self.logger.info(f"PESS Client initialized ({status})")
    
    async def record_session_start(self, ticket_id: str, session_id: str, metadata: Dict = None):
        """
        Record the start of a development session.
        
        Args:
            ticket_id: Jira ticket ID
            session_id: Session identifier  
            metadata: Additional session metadata
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            payload = {
                "event": "session_start",
                "ticket_id": ticket_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            
            if self.base_url:
                await self._send_event(payload)
            else:
                self.logger.debug(f"Mock PESS: Session start recorded for {ticket_id}")
                
        except Exception as e:
            self.logger.error(f"Error recording session start: {str(e)}")
    
    async def record_prompt_generated(self, ticket_id: str, session_id: str, prompt_hash: str, 
                                    template_used: str, enrichment_data: Dict = None):
        """
        Record prompt generation for scoring.
        
        Args:
            ticket_id: Jira ticket ID
            session_id: Session identifier
            prompt_hash: Hash of the generated prompt
            template_used: Template name used
            enrichment_data: Synthetic memory enrichment data
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            payload = {
                "event": "prompt_generated", 
                "ticket_id": ticket_id,
                "session_id": session_id,
                "prompt_hash": prompt_hash,
                "template_used": template_used,
                "timestamp": time.time(),
                "enrichment_data": enrichment_data or {}
            }
            
            if self.base_url:
                await self._send_event(payload)
            else:
                self.logger.debug(f"Mock PESS: Prompt generated for {ticket_id} using {template_used}")
                
        except Exception as e:
            self.logger.error(f"Error recording prompt generation: {str(e)}")
    
    async def score_session_completion(
        self,
        ticket_id: str,
        session_id: str,
        pr_url: str = None,
        files_modified: list = None,
        processing_time_ms: int = None,
        retry_count: int = 1,
        feedback: Optional[str] = None,
        agent_telemetry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Score a completed development session.
        
        Args:
            ticket_id: Jira ticket ID
            session_id: Session identifier
            pr_url: Pull request URL (optional)
            files_modified: List of modified files
            processing_time_ms: Processing time in milliseconds
            retry_count: Number of retries/iterations
        
        Returns:
            PESS scoring response with score and recommendations
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            payload = {
                "ticket_id": ticket_id,
                "session_id": session_id,
                "pr_url": pr_url,
                "files_modified": files_modified or [],
                "processing_time_ms": processing_time_ms,
                "retry_count": retry_count,
                "feedback": feedback,
                "agent_telemetry": agent_telemetry or {},
                "timestamp": time.time()
            }
            
            if self.base_url:
                return await self._submit_scoring(payload)
            else:
                return self._generate_mock_score(payload)
                
        except Exception as e:
            self.logger.error(f"Error scoring session completion: {str(e)}")
            return self._generate_mock_score({"ticket_id": ticket_id, "error": str(e)})
    
    async def _send_event(self, payload: Dict):
        """Send event data to PESS system"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/events",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
        except Exception as e:
            self.logger.warning(f"Failed to send PESS event: {str(e)}")
    
    async def _submit_scoring(self, payload: Dict) -> Dict[str, Any]:
        """Submit scoring payload to PESS system"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/score",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            self.logger.warning(f"PESS request failed: {e}")
            return self._generate_mock_score(payload)
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"PESS HTTP error: {e}")
            return self._generate_mock_score(payload)
    
    def _generate_mock_score(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate mock PESS response for development/fallback.
        
        Args:
            payload: Original scoring request
        
        Returns:
            Mock scoring response with realistic heuristics
        """
        # Extract data for scoring heuristics
        files_count = len(payload.get("files_modified", []))
        retry_count = payload.get("retry_count", 1)
        processing_time = payload.get("processing_time_ms", 0)
        
        # Base score starts high and decreases with complexity/issues
        base_score = 0.90
        
        # File complexity penalty (more files = more complex = potentially lower quality)
        file_penalty = min(0.15, files_count * 0.02)
        
        # Retry penalty (more retries = initial prompt wasn't clear enough)
        retry_penalty = min(0.25, (retry_count - 1) * 0.12)
        
        # Processing time bonus/penalty (very fast might indicate simple ticket)
        if processing_time > 0:
            if processing_time < 1000:  # Very fast (< 1 second)
                time_adjustment = 0.05  # Slight penalty - might be too simple
            elif processing_time > 30000:  # Very slow (> 30 seconds)
                time_adjustment = -0.10  # Penalty - might indicate issues
            else:
                time_adjustment = 0.02  # Bonus for reasonable processing time
        else:
            time_adjustment = 0
        
        # Calculate final score
        final_score = max(0.1, base_score - file_penalty - retry_penalty + time_adjustment)
        
        # Determine clarity rating
        if final_score >= 0.85:
            clarity = "High"
        elif final_score >= 0.70:
            clarity = "Medium"
        elif final_score >= 0.50:
            clarity = "Low" 
        else:
            clarity = "Very Low"
        
        # Generate actionable recommendations
        recommendations = []
        if retry_count > 1:
            recommendations.append("Consider improving prompt clarity to reduce iterations")
        if files_count > 5:
            recommendations.append("Complex multi-file changes - consider breaking into smaller tasks")
        if processing_time > 30000:
            recommendations.append("Long processing time - optimize template for faster agent execution")
        if final_score >= 0.85:
            recommendations.append("Excellent performance - consider using this template as a reference")
        
        recommendation_text = "; ".join(recommendations) if recommendations else "Good prompt quality maintained"
        
        prompt_score = round(final_score, 2)

        result = {
            "prompt_score": prompt_score,
            "score_percent": round(prompt_score * 100, 1),
            "clarity_rating": clarity,
            "edit_similarity": round(max(0.1, final_score - 0.05), 2),
            "risk_score": round(max(0.0, 1.0 - final_score), 2),
            "recommendation": recommendation_text,
            "processing_time_ms": processing_time,
            "files_affected": files_count,
            "retry_count": retry_count,
            "mock_response": True,  # Indicate this is a mock for development
            "algorithm_version": "mock_0.1",
        }

        if payload.get("feedback"):
            result["feedback"] = payload.get("feedback")
        if payload.get("agent_telemetry"):
            result["agent_telemetry"] = payload.get("agent_telemetry")

        return result
