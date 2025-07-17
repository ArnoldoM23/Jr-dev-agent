"""
Template Intelligence Service Client

HTTP client for communicating with the Template Intelligence microservice.
"""

import httpx
import logging
from typing import Dict, Any, List
import os


class TemplateIntelligenceClient:
    """Client for the Template Intelligence microservice"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("TEMPLATE_INTELLIGENCE_URL", "http://localhost:8002")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)
    
    async def select_template(self, ticket_data: Dict[str, Any]) -> str:
        """
        Select the best template for a ticket
        
        Args:
            ticket_data: Ticket metadata
            
        Returns:
            Selected template name
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/select",
                json={"ticket_data": ticket_data}
            )
            response.raise_for_status()
            
            result = response.json()
            return result["selected_template"]
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error calling Template Intelligence: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error calling Template Intelligence: {e}")
            raise
    
    async def validate_template(self, template_name: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ticket data against a template
        
        Args:
            template_name: Template to validate against
            ticket_data: Ticket metadata
            
        Returns:
            Validation result
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/validate",
                json={
                    "template_name": template_name,
                    "ticket_data": ticket_data
                }
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error validating template: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error validating template: {e}")
            raise
    
    async def get_templates(self) -> Dict[str, Any]:
        """Get all available templates"""
        try:
            response = await self.client.get(f"{self.base_url}/templates")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting templates: {e}")
            raise
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of the Template Intelligence service"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting Template Intelligence health: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
template_intelligence_client = TemplateIntelligenceClient() 