"""
PromptBuilder Service Client

HTTP client for communicating with the PromptBuilder microservice.
"""

import httpx
import logging
from typing import Dict, Any, Optional
import os


class PromptBuilderClient:
    """Client for the PromptBuilder microservice"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("PROMPTBUILDER_URL", "http://localhost:8001")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)
    
    async def generate_prompt(self, template_name: str, ticket_data: Dict[str, Any], 
                            enrichment_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt using the PromptBuilder service
        
        Args:
            template_name: Name of the template to use
            ticket_data: Ticket metadata
            enrichment_data: Optional enrichment data
            
        Returns:
            Generated prompt string
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/generate",
                json={
                    "template_name": template_name,
                    "ticket_data": ticket_data,
                    "enrichment_data": enrichment_data
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result["prompt"]
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error calling PromptBuilder: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error calling PromptBuilder: {e}")
            raise
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of the PromptBuilder service"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting PromptBuilder health: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
promptbuilder_client = PromptBuilderClient() 