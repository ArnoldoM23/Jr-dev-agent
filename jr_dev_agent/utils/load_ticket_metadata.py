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
import re
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from dataclasses import dataclass
from datetime import datetime

# Local MCP client wrappers (support real + mock flows)
from jr_dev_agent.clients import JiraMCPClient
from jr_dev_agent.utils.description_parser import extract_template_from_description

# Setup structured logging
logger = structlog.get_logger(__name__)

# Configuration
JIRA_MCP_URL = os.getenv("JIRA_MCP_URL", "https://mcp.walmart.com/api/jira")
JIRA_TIMEOUT = int(os.getenv("JIRA_TIMEOUT", "5"))
FALLBACK_DIR = Path(__file__).parent.parent / "fallback"
FALLBACK_FILE = FALLBACK_DIR / "jira_prompt.json"
FALLBACK_TEMPLATE_FILE = FALLBACK_DIR / "jira_ticket_template.txt"
REPO_TEMPLATE_FILE = Path.cwd() / "jira_ticket_template.txt"

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
    prompt_text: Optional[str] = None

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
            "additional_context": self.additional_context,
            "prompt_text": self.prompt_text
        }

class JiraFallbackError(Exception):
    """Exception raised when fallback loading fails"""
    pass

class JiraAPIError(Exception):
    """Exception raised when Jira API fails"""
    pass

def load_ticket_metadata(ticket_id: str, fallback_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Load ticket metadata with fallback mechanism.
    
    Args:
        ticket_id: Jira ticket ID (e.g., "CEPG-67890")
        fallback_content: Optional raw content string from client (e.g. from local file)
        
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
        timeout=JIRA_TIMEOUT,
        has_fallback_content=bool(fallback_content)
    )
    
    # Priority 0: Explicitly provided fallback content (from client via MCP tool arg)
    # This takes precedence over everything, even Jira MCP, as it implies manual override
    if fallback_content:
        logger.info(f"Using provided fallback content for {ticket_id}")
        parsed = parse_text_template_content(fallback_content, ticket_id)
        
        if not parsed:
             raise ValueError("Client-provided fallback content failed to parse. Please check the template format.")
             
        try:
             result = validate_ticket_metadata(parsed).to_dict()
             result["_fallback_used"] = "client_provided_content"
             return result
        except ValueError as e:
             logger.error(f"Client provided content validation failed: {e}")
             raise ValueError(f"Client-provided fallback content is invalid: {e}")

    # Check if dev mode is enabled (force fallback)
    if os.getenv("DEV_MODE", "false").lower() == "true":
        logger.info(
            "Dev mode enabled - using fallback",
            ticket_id=ticket_id,
            dev_mode=True
        )
        # Try Text Template first even in Dev Mode
        text_metadata = load_from_text_template(ticket_id)
        if text_metadata:
            try:
                result = validate_ticket_metadata(text_metadata).to_dict()
                result["_fallback_used"] = "text_template"
                return result
            except ValueError as e:
                logger.warning(f"Text template validation failed: {e}. Falling back to JSON.")
                
        return load_from_fallback(ticket_id)
    
    # Attempt to use the Jira MCP client when configured
    client = JiraMCPClient()
    if client.configured:
        try:
            logger.info("Fetching ticket from Jira MCP", ticket_id=ticket_id, url=client.base_url)
            metadata = client.fetch_ticket(ticket_id)
            if not metadata:
                raise ValueError("Empty payload from Jira MCP")
            return validate_ticket_metadata(metadata).to_dict()
        except Exception as exc:
            logger.warning(
                "Jira MCP fetch failed - falling back to local data",
                ticket_id=ticket_id,
                error=str(exc)
            )
    
    # MCP not available or failed - trigger fallback chain
    logger.info(f"[MCP Fallback Triggered] Reason: MCP unavailable for {ticket_id}")
    
    # Step 1: Check for manual text template (Server-side disk check)
    text_metadata = load_from_text_template(ticket_id)
    if text_metadata:
        try:
            result = validate_ticket_metadata(text_metadata).to_dict()
            result["_fallback_used"] = "text_template"
            return result
        except ValueError as e:
            logger.warning(f"Text template validation failed: {e}. Falling back to JSON.")

    # Step 2: Fallback to static JSON
    return load_from_fallback(ticket_id)

def parse_text_template_content(content: str, ticket_id: str) -> Optional[Dict[str, Any]]:
    """
    Parse raw text content into ticket metadata structure.
    
    Args:
        content: Raw string content of the template
        ticket_id: Default ticket ID if not overridden in content
        
    Returns:
        Dictionary of metadata or None if parsing fails
    """
    try:
        if not content.strip():
            return None
            
        # 1. Extract Ticket ID override from content
        # Format: Jira_Ticket: CEPG-67890
        file_ticket_id = None
        ticket_match = re.search(r"Jira_Ticket:\s*([A-Z]+-\d+)", content, re.IGNORECASE)
        if ticket_match:
             file_ticket_id = ticket_match.group(1).strip()
             if file_ticket_id:
                 # Use the ID from the content as it's explicitly entered by the dev
                 ticket_id = file_ticket_id
        
        # 2. Extract Description/Template content
        separator_match = re.search(r"Paste Template below\s*-+", content, re.IGNORECASE)
        
        if separator_match:
            description_text = content[separator_match.end():].strip()
        else:
            # Fallback: strip header line if no separator found
            lines = [l for l in content.splitlines() if not l.strip().lower().startswith("jira_ticket:")]
            description_text = "\n".join(lines).strip()
            
        if not description_text:
            logger.warning("Text template content is empty after stripping header")
            return None
            
        # 3. Parse description for template structure
        extracted = extract_template_from_description(description_text) or {}
        
        # Map Reference_Files to files_affected
        files_affected = []
        # Check keys case-insensitively (parser returns lowercase keys if YAML parsed)
        if "reference_files" in extracted and isinstance(extracted["reference_files"], list):
            files_affected = extracted["reference_files"]
        elif "Reference_Files" in extracted and isinstance(extracted["Reference_Files"], list):
            files_affected = extracted["Reference_Files"]
        elif "file_references" in extracted and isinstance(extracted["file_references"], list):
            files_affected = extracted["file_references"]
        elif "files_affected" in extracted and isinstance(extracted["files_affected"], list):
            files_affected = extracted["files_affected"]
            
        # 4. Construct metadata
        metadata = {
            "ticket_id": ticket_id,
            "template_name": extracted.get("name", "feature"),
            "summary": extracted.get("feature", f"Task {ticket_id}"),
            "description": description_text,
            "feature": extracted.get("feature", "unknown_feature"),
            "prompt_text": extracted.get("prompt_text"),
            "priority": "medium",
            "story_points": 0,
            "labels": [],
            "files_affected": files_affected,
            "acceptance_criteria": [],
            "_fallback_used": "text_template"
        }
        
        return metadata
        
    except Exception as e:
        logger.warning(f"Failed to parse text template content: {e}")
        return None

def load_from_text_template(ticket_id: str) -> Optional[Dict[str, Any]]:
    """
    Load metadata from manual text template fallback file (Server Side).
    
    Args:
        ticket_id: Ticket ID to verify against or use
        
    Returns:
        Dictionary of metadata or None if not found/empty
    """
    try:
        # Priority 1: Check Repo Root (CWD)
        target_file = None
        if REPO_TEMPLATE_FILE.exists():
            target_file = REPO_TEMPLATE_FILE
            logger.info(f"Found text template in repo root: {REPO_TEMPLATE_FILE}")
        # Priority 2: Check Internal Fallback (for dev/testing)
        elif FALLBACK_TEMPLATE_FILE.exists():
            target_file = FALLBACK_TEMPLATE_FILE
            logger.info(f"Using internal text template fallback: {FALLBACK_TEMPLATE_FILE}")
            
        if not target_file:
            return None
            
        content = target_file.read_text(encoding="utf-8")
        logger.info(f"Checking text template fallback: {target_file}")
        
        return parse_text_template_content(content, ticket_id)
        
    except Exception as e:
        logger.warning(f"Failed to load from text template: {e}")
        return None

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
        
        # In dev mode, adapt fallback data to requested ticket ID
        fallback_ticket_id = fallback_data.get("ticket_id")
        if fallback_ticket_id != ticket_id:
            logger.info(
                "Adapting fallback data for dev mode",
                original_ticket=fallback_ticket_id,
                requested_ticket=ticket_id,
                dev_mode=True
            )
            # Use fallback data as template and adapt to requested ticket ID
            fallback_data["ticket_id"] = ticket_id
            # Update summary to reflect the new ticket ID  
            original_summary = fallback_data.get("summary", "")
            fallback_data["summary"] = f"{original_summary} (adapted from {fallback_ticket_id})"
        
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
    # Attempt to extract template info from description if available
    if "description" in metadata and metadata["description"]:
        try:
            extracted_template = extract_template_from_description(metadata["description"])
            if extracted_template:
                logger.info("Enriching metadata from description template", 
                           template_name=extracted_template.get("name"))
                
                # Map extracted fields to metadata
                if "name" in extracted_template:
                    metadata["template_name"] = extracted_template["name"]
                if "prompt_text" in extracted_template:
                    metadata["prompt_text"] = extracted_template["prompt_text"]
                
                # Map optional fields if they exist in template but not in metadata
                for field in ["feature", "summary"]:
                    if field in extracted_template and field not in metadata:
                        metadata[field] = extracted_template[field]
                        
        except Exception as e:
            logger.warning("Failed to extract template from description", error=str(e))

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
        additional_context=metadata.get("additional_context", {}),
        prompt_text=metadata.get("prompt_text")
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
        
        # Write plain text template as well
        try:
            lines = []
            lines.append(f"Jira_Ticket: {ticket_id}")
<<<<<<< HEAD
            lines.append("")
=======
            lines.append("\n")
>>>>>>> ee3b3d0e49de276bed59f8169d11481ef9030b27
            lines.append("Paste Template below")
            lines.append("-" * 100)
            
            lines.append(f"Name: {metadata.get('template_name', 'feature')}")
            if metadata.get('feature'):
                lines.append(f"Feature: {metadata.get('feature')}")
            
            # Handle description
            desc = metadata.get('description', '')
            if desc:
                lines.append("Description: |")
                for line in desc.splitlines():
                    lines.append(f"  {line}")
            
            # Handle prompt_text
            prompt = metadata.get('prompt_text', '')
            if prompt:
                lines.append("Prompt_Text: |")
                for line in prompt.splitlines():
                    lines.append(f"  {line}")

            # Handle files
            files = metadata.get('files_affected', [])
            if files:
                lines.append("Reference_Files:")
                for f in files:
                    lines.append(f"  - {f}")
                    
            text_content = "\n".join(lines)
            FALLBACK_TEMPLATE_FILE.write_text(text_content, encoding="utf-8")
            logger.info(f"Created text template fallback: {FALLBACK_TEMPLATE_FILE}")
            
        except Exception as text_error:
            logger.warning(f"Failed to generate text template fallback: {text_error}")
        
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
