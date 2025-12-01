import re
import yaml
import textwrap
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

def extract_template_from_description(description: str) -> Optional[Dict[str, Any]]:
    """
    Extract a YAML template definition from a Jira ticket description.
    
    Supports:
    1. Full description being a YAML document.
    2. YAML embedded in a ```yaml ... ``` code block.
    
    Args:
        description: The text content of the Jira description.
        
    Returns:
        Dictionary of extracted template fields, or None if no valid YAML found.
    """
    if not description or not description.strip():
        return None
        
    # Strategy 1: Check for explicit YAML code block
    # We use a non-greedy match for the content
    yaml_block_pattern = re.compile(r"```yaml\s+(.*?)\s+```", re.DOTALL | re.IGNORECASE)
    match = yaml_block_pattern.search(description)
    
    yaml_content = None
    
    if match:
        yaml_content = match.group(1)
        # Dedent the content to handle indentation issues
        yaml_content = textwrap.dedent(yaml_content)
        logger.debug("Found YAML code block in description")
    else:
        # Strategy 2: Attempt to parse the entire description as YAML
        # (Use a heuristic to check if it looks like YAML key-values)
        if ":" in description and "name:" in description:
             yaml_content = description
             # Attempt dedent just in case
             yaml_content = textwrap.dedent(yaml_content)
             logger.debug("Attempting to parse full description as YAML")

    if yaml_content:
        try:
            data = yaml.safe_load(yaml_content)
            if isinstance(data, dict):
                logger.info("Successfully extracted template from description", 
                            template_name=data.get('name'))
                return data
        except yaml.YAMLError as e:
            logger.warning("Failed to parse YAML from description", error=str(e))
            
    # Strategy 3: Regex Fallback for "dirty" YAML or partial template
    # This handles cases where copy-paste artifacts (like "reference files" lines) break strict YAML
    if ":" in description and "name:" in description:
        logger.debug("Attempting regex fallback for template extraction")
        extracted = {}
        
        # Extract name
        name_match = re.search(r"^name:\s*(.+)$", description, re.MULTILINE)
        if name_match:
            extracted["name"] = name_match.group(1).strip()
            
        # Extract prompt_text
        # Look for prompt_text: followed by optional | or >
        # Capture until next root-level key (word:) or end of string
        prompt_match = re.search(r"^prompt_text:\s*[|>]?(.*?)(?=^[\w-]+:|\Z)", description, re.MULTILINE | re.DOTALL)
        if prompt_match:
            extracted["prompt_text"] = prompt_match.group(1).strip()
            
        # Extract feature if present
        feature_match = re.search(r"^feature:\s*(.+)$", description, re.MULTILINE)
        if feature_match:
            extracted["feature"] = feature_match.group(1).strip()

        if extracted.get("name") or extracted.get("prompt_text"):
             logger.info("Successfully extracted template via regex fallback", 
                        template_name=extracted.get("name"))
             return extracted

    return None

