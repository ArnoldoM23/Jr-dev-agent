import logging
import os
import json
import base64
import time
import httpx
from typing import Dict, Any, Optional

from jr_dev_agent.models.mcp import CreateTemplatePRArgs, CreateTemplatePRResult

logger = logging.getLogger(__name__)

# Template name to file path mapping
TEMPLATE_FILE_MAP = {
    "feature": "featurePromptTemplates/feature_resolver_change.yaml",
    "bugfix": "bugFixPromptTemplates/bug_fix.yaml",
    "config_update": "configPromptTemplates/config_update.yaml",
    "schema_change": "schemaPromptTemplates/feature_schema_change.yaml",
    "feature_schema_change": "schemaPromptTemplates/feature_schema_change.yaml",
    # Fallback/Guessed paths based on directory structure
    "test_generation": "testGenerationPromptTemplates/test_generation.yaml",
    "version_upgrade": "versionUpgradePromptTemplates/version_upgrade.yaml",
    "refactor": "featurePromptTemplates/feature_resolver_change.yaml" # Fallback to feature for now or needs specific path
}

async def handle_create_template_pr(args: CreateTemplatePRArgs) -> Dict[str, Any]:
    """
    Handle create_template_pr tool - create a PR to update a prompt template
    """
    logger.info(f"Creating PR to update template: {args.template_name}")
    
    # 1. Load Configuration
    config = _load_config()
    if not config:
        return _error_response("Configuration not found or invalid.")
    
    repo_url = config.get("repository_url")
    auth_token = config.get("auth_token")
    
    if not repo_url or not auth_token:
        return _error_response("Missing 'prompt_templates' configuration in config.json.")
        
    # Parse Owner/Repo from URL (e.g., https://github.com/ArnoldoM23/jr-dev-agent-prompt-templates)
    try:
        parts = repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
    except IndexError:
        return _error_response(f"Invalid repository URL format: {repo_url}")

    # Resolve Auth Token (env var support)
    if auth_token.startswith("env:"):
        env_var = auth_token.split(":", 1)[1]
        token = os.getenv(env_var)
        if not token:
            return _error_response(f"Environment variable {env_var} not set.")
    else:
        token = auth_token

    # 2. Resolve File Path
    file_path = TEMPLATE_FILE_MAP.get(args.template_name)
    if not file_path:
        # Try to guess or fail? Let's fail for safety or check if it looks like a path
        if "/" in args.template_name:
             file_path = args.template_name
        else:
            return _error_response(f"Unknown template name: {args.template_name}. Supported: {list(TEMPLATE_FILE_MAP.keys())}")

    # 3. GitHub API Interaction
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=30.0) as client:
        try:
            # A. Get Main Branch SHA
            resp = await client.get(f"/repos/{owner}/{repo}/git/ref/heads/main")
            if resp.status_code != 200:
                return _error_response(f"Failed to fetch main branch: {resp.text}")
            
            main_sha = resp.json()["object"]["sha"]
            
            # B. Create New Branch
            branch_name = f"update-template-{args.template_name}-{int(time.time())}"
            resp = await client.post(f"/repos/{owner}/{repo}/git/refs", json={
                "ref": f"refs/heads/{branch_name}",
                "sha": main_sha
            })
            if resp.status_code != 201:
                return _error_response(f"Failed to create branch {branch_name}: {resp.text}")
            
            # C. Get File SHA (if it exists)
            resp = await client.get(f"/repos/{owner}/{repo}/contents/{file_path}?ref={branch_name}")
            file_sha = None
            if resp.status_code == 200:
                file_sha = resp.json()["sha"]
            
            # D. Update (or Create) File
            content_encoded = base64.b64encode(args.updated_content.encode("utf-8")).decode("utf-8")
            payload = {
                "message": f"Update {args.template_name} template",
                "content": content_encoded,
                "branch": branch_name
            }
            if file_sha:
                payload["sha"] = file_sha
            
            resp = await client.put(f"/repos/{owner}/{repo}/contents/{file_path}", json=payload)
            if resp.status_code not in [200, 201]:
                return _error_response(f"Failed to update file {file_path}: {resp.text}")
            
            # E. Create Pull Request
            pr_payload = {
                "title": args.pr_title,
                "body": args.pr_description,
                "head": branch_name,
                "base": "main"
            }
            resp = await client.post(f"/repos/{owner}/{repo}/pulls", json=pr_payload)
            if resp.status_code != 201:
                return _error_response(f"Failed to create PR: {resp.text}")
            
            pr_data = resp.json()
            pr_url = pr_data["html_url"]
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully created PR to update template: {pr_url}"
                    }
                ],
                "_meta": {"pr_url": pr_url, "status": "success"}
            }

        except Exception as e:
            logger.exception("GitHub API error")
            return _error_response(f"GitHub API Error: {str(e)}")

def _load_config() -> Optional[Dict]:
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                data = json.load(f)
                return data.get("prompt_templates", {})
        return None
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def _error_response(message: str) -> Dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": f"Error creating Template PR: {message}"
            }
        ],
        "isError": True,
        "_meta": {"status": "error", "error": message}
    }
