"""
🚀 Jr Dev Agent - MVP Jira Fallback Flow
==========================================

This module provides a fallback mechanism for loading Jira ticket metadata
when the MCP server is unavailable or offline. It enables developers to
continue working with local fallback data.

Flow:
1. Try to fetch from Jira MCP API with 5-second timeout
2. On failure, fall back to local jira_prompt.json
3. Validate ticket ID matches fallback data
4. Return same metadata shape for seamless integration

Author: Jr Dev Agent Team
Version: 1.0
"""

import json
import os
import requests
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from dataclasses import dataclass
from datetime import datetime

# Setup structured logging
logger = structlog.get_logger(__name__)

# Configuration
JIRA_MCP_URL = os.getenv("JIRA_MCP_URL", "https://mcp.walmart.com/api/jira")
JIRA_TIMEOUT = int(os.getenv("JIRA_TIMEOUT", "5"))
FALLBACK_DIR = Path(__file__).parent.parent / "fallback"
FALLBACK_FILE = FALLBACK_DIR / "jira_prompt.json"

@dataclass
class JiraMetadata:
    """Structured representation of Jira ticket metadata"""
    ticket_id: str
    template_name: str
    summary: str
    description: str
    acceptance_criteria: list
    files_affected: list
    feature: str
    priority: str = "medium"
    story_points: int = 0
    labels: list = None
    component: str = ""
    assignee: str = ""
    reporter: str = ""
    created_date: str = ""
    updated_date: str = ""
    epic_link: str = ""
    sprint: str = ""
    additional_context: dict = None

    def __post_init__(self):
        """Initialize default values"""
        if self.labels is None:
            self.labels = []
        if self.additional_context is None:
            self.additional_context = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ticket_id": self.ticket_id,
            "template_name": self.template_name,
            "summary": self.summary,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "files_affected": self.files_affected,
            "feature": self.feature,
            "priority": self.priority,
            "story_points": self.story_points,
            "labels": self.labels,
            "component": self.component,
            "assignee": self.assignee,
            "reporter": self.reporter,
            "created_date": self.created_date,
            "updated_date": self.updated_date,
            "epic_link": self.epic_link,
            "sprint": self.sprint,
            "additional_context": self.additional_context
        }

class JiraFallbackError(Exception):
    """Exception raised when fallback loading fails"""
    pass

class JiraAPIError(Exception):
    """Exception raised when Jira API fails"""
    pass

def load_ticket_metadata(ticket_id: str) -> Dict[str, Any]:
    """
    Load ticket metadata with fallback mechanism.
    
    Args:
        ticket_id: Jira ticket ID (e.g., "CEPG-67890")
        
    Returns:
        Dictionary containing ticket metadata
        
    Raises:
        JiraFallbackError: If fallback loading fails
        ValueError: If ticket ID is invalid
    """
    if not ticket_id or not ticket_id.strip():
        raise ValueError("Ticket ID cannot be empty")
    
    # Log the attempt
    logger.info(
        "Loading ticket metadata",
        ticket_id=ticket_id,
        jira_url=JIRA_MCP_URL,
        timeout=JIRA_TIMEOUT
    )
    
    # Check if dev mode is enabled (force fallback)
    if os.getenv("DEV_MODE", "false").lower() == "true":
        logger.info(
            "Dev mode enabled - using fallback",
            ticket_id=ticket_id,
            dev_mode=True
        )
        return load_from_fallback(ticket_id)
    
    # Try to fetch from Jira MCP API
    try:
        logger.info(f"Fetching from MCP: {ticket_id}")
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Jr-Dev-Agent/1.0"
        }
        
        # Add authentication if available
        api_key = os.getenv("JIRA_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        response = requests.get(
            f"{JIRA_MCP_URL}/{ticket_id}",
            headers=headers,
            timeout=JIRA_TIMEOUT
        )
        
        response.raise_for_status()
        
        metadata = response.json()
        
        logger.info(
            "Successfully fetched from MCP",
            ticket_id=ticket_id,
            template_name=metadata.get("template_name"),
            response_time=response.elapsed.total_seconds()
        )
        
        return metadata
        
    except requests.exceptions.Timeout:
        logger.warning(
            "MCP request timed out - falling back to local data",
            ticket_id=ticket_id,
            timeout=JIRA_TIMEOUT
        )
        
    except requests.exceptions.ConnectionError as e:
        logger.warning(
            "MCP connection failed - falling back to local data",
            ticket_id=ticket_id,
            error=str(e)
        )
        
    except requests.exceptions.HTTPError as e:
        logger.warning(
            "MCP HTTP error - falling back to local data",
            ticket_id=ticket_id,
            status_code=e.response.status_code,
            error=str(e)
        )
        
    except Exception as e:
        logger.warning(
            "Unexpected MCP error - falling back to local data",
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
    
    # MCP failed - trigger fallback
    logger.info(f"[MCP Fallback Triggered] Reason: MCP unavailable for {ticket_id}")
    return load_from_fallback(ticket_id)

def load_from_fallback(ticket_id: str) -> Dict[str, Any]:
    """
    Load ticket metadata from local fallback file.
    
    Args:
        ticket_id: Jira ticket ID to validate against fallback data
        
    Returns:
        Dictionary containing fallback ticket metadata
        
    Raises:
        JiraFallbackError: If fallback loading fails
        ValueError: If ticket ID doesn't match fallback data
    """
    try:
        if not FALLBACK_FILE.exists():
            raise JiraFallbackError(f"Fallback file not found: {FALLBACK_FILE}")
        
        logger.info(
            "Loading from fallback file",
            ticket_id=ticket_id,
            fallback_file=str(FALLBACK_FILE)
        )
        
        with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
            fallback_data = json.load(f)
        
        # Validate ticket ID matches fallback data
        fallback_ticket_id = fallback_data.get("ticket_id")
        if fallback_ticket_id != ticket_id:
            raise ValueError(
                f"Fallback file does not match ticket: {ticket_id}. "
                f"Expected: {fallback_ticket_id}"
            )
        
        # Add fallback metadata
        fallback_data["_fallback_used"] = True
        fallback_data["_fallback_timestamp"] = datetime.now().isoformat()
        fallback_data["_fallback_file"] = str(FALLBACK_FILE)
        
        logger.info(
            "Successfully loaded from fallback",
            ticket_id=ticket_id,
            template_name=fallback_data.get("template_name"),
            fallback_used=True
        )
        
        return fallback_data
        
    except FileNotFoundError:
        raise JiraFallbackError(f"Fallback file not found: {FALLBACK_FILE}")
        
    except json.JSONDecodeError as e:
        raise JiraFallbackError(f"Invalid JSON in fallback file: {e}")
        
    except Exception as e:
        raise JiraFallbackError(f"Failed to load fallback data: {e}")

def validate_ticket_metadata(metadata: Dict[str, Any]) -> JiraMetadata:
    """
    Validate and structure ticket metadata.
    
    Args:
        metadata: Raw metadata dictionary
        
    Returns:
        Validated JiraMetadata object
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = [
        "ticket_id", "template_name", "summary", 
        "description", "acceptance_criteria", "files_affected", "feature"
    ]
    
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")
    
    return JiraMetadata(
        ticket_id=metadata["ticket_id"],
        template_name=metadata["template_name"],
        summary=metadata["summary"],
        description=metadata["description"],
        acceptance_criteria=metadata["acceptance_criteria"],
        files_affected=metadata["files_affected"],
        feature=metadata["feature"],
        priority=metadata.get("priority", "medium"),
        story_points=metadata.get("story_points", 0),
        labels=metadata.get("labels", []),
        component=metadata.get("component", ""),
        assignee=metadata.get("assignee", ""),
        reporter=metadata.get("reporter", ""),
        created_date=metadata.get("created_date", ""),
        updated_date=metadata.get("updated_date", ""),
        epic_link=metadata.get("epic_link", ""),
        sprint=metadata.get("sprint", ""),
        additional_context=metadata.get("additional_context", {})
    )

def create_fallback_file(ticket_id: str, metadata: Dict[str, Any]) -> None:
    """
    Create or update fallback file with ticket metadata.
    
    Args:
        ticket_id: Jira ticket ID
        metadata: Ticket metadata to save
    """
    try:
        # Ensure fallback directory exists
        FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        
        # Write fallback data
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(
            "Created fallback file",
            ticket_id=ticket_id,
            fallback_file=str(FALLBACK_FILE)
        )
        
    except Exception as e:
        logger.error(
            "Failed to create fallback file",
            ticket_id=ticket_id,
            error=str(e)
        )
        raise

def get_fallback_status() -> Dict[str, Any]:
    """
    Get status information about the fallback system.
    
    Returns:
        Dictionary with fallback status information
    """
    return {
        "fallback_file_exists": FALLBACK_FILE.exists(),
        "fallback_file_path": str(FALLBACK_FILE),
        "fallback_file_size": FALLBACK_FILE.stat().st_size if FALLBACK_FILE.exists() else 0,
        "dev_mode": os.getenv("DEV_MODE", "false").lower() == "true",
        "jira_mcp_url": JIRA_MCP_URL,
        "jira_timeout": JIRA_TIMEOUT,
        "last_modified": (
            datetime.fromtimestamp(FALLBACK_FILE.stat().st_mtime).isoformat()
            if FALLBACK_FILE.exists() else None
        )
    }

# Example usage and testing
if __name__ == "__main__":
    # Test the fallback system
    test_ticket_id = "CEPG-67890"
    
    print("🧪 Testing Jr Dev Agent - MVP Jira Fallback Flow")
    print("=" * 50)
    
    try:
        # Test fallback status
        status = get_fallback_status()
        print(f"📊 Fallback Status: {status}")
        
        # Test loading metadata
        metadata = load_ticket_metadata(test_ticket_id)
        print(f"✅ Successfully loaded metadata for {test_ticket_id}")
        print(f"📋 Template: {metadata.get('template_name')}")
        print(f"📝 Summary: {metadata.get('summary')}")
        print(f"🔄 Fallback used: {metadata.get('_fallback_used', False)}")
        
        # Test validation
        validated = validate_ticket_metadata(metadata)
        print(f"✅ Validation passed: {validated.ticket_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise 