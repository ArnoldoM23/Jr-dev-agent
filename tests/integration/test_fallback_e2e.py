import sys
import os
import asyncio
import logging
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_fallback_test")

from jr_dev_agent.utils.load_ticket_metadata import load_ticket_metadata, FALLBACK_TEMPLATE_FILE
from jr_dev_agent.services.prompt_builder import PromptBuilder

# Sample template content that includes structured data (Labels as list of dicts potential)
# We simulate what a user might paste
SAMPLE_TEMPLATE = """Jira_Ticket: CEPG-E2E-TEST

Paste Template below
------------------------------------------------------------------------------------------------------
Name: feature_schema_change
Description: |
  End-to-end test description.
Prompt_Text: |
  You are an AI agent.
Reference_Files:
  - "src/test.ts"
Labels:
  - feature
  - e2e
"""

async def test_fallback_e2e_flow():
    logger.info("🚀 Starting E2E Manual Fallback Integration Test")
    
    # Backup existing fallback file if it exists
    backup_path = Path(str(FALLBACK_TEMPLATE_FILE) + ".bak")
    if FALLBACK_TEMPLATE_FILE.exists():
        shutil.copy(FALLBACK_TEMPLATE_FILE, backup_path)
        logger.info("Backed up existing template file")
        
    try:
        # 1. Setup: Write the template file
        FALLBACK_TEMPLATE_FILE.write_text(SAMPLE_TEMPLATE, encoding="utf-8")
        logger.info(f"📝 Wrote sample template to {FALLBACK_TEMPLATE_FILE}")
        
        # 2. Step: Load Metadata (Simulate Agent Step 1)
        logger.info("🔄 Loading ticket metadata (should trigger text fallback)...")
        # Force dev mode to ensure we don't hit real Jira, or just rely on fallback
        os.environ["DEV_MODE"] = "true" 
        
        ticket_data = load_ticket_metadata("CEPG-E2E-TEST")
        
        if not ticket_data:
            logger.error("❌ Failed to load ticket data")
            return False
            
        if ticket_data.get("_fallback_used") != "text_template":
            logger.error(f"❌ Did not use text template fallback! Used: {ticket_data.get('_fallback_used')}")
            return False
            
        logger.info(f"✅ Loaded metadata: {ticket_data['ticket_id']}")
        logger.info(f"   Labels: {ticket_data.get('labels')}")
        logger.info(f"   Files: {ticket_data.get('files_affected')}")
        
        # 3. Step: Generate Prompt (Simulate Agent Step 2)
        logger.info("🎨 Generating prompt using PromptBuilder...")
        builder = PromptBuilder()
        await builder.initialize()
        
        prompt = await builder.generate_prompt("feature", ticket_data)
        
        if not prompt or len(prompt) < 10:
            logger.error("❌ Generated prompt is empty or too short")
            return False
            
        if "You are an AI agent" not in prompt:
            logger.error("❌ Prompt missing content from template Prompt_Text")
            return False
            
        logger.info(f"✅ Prompt generated successfully ({len(prompt)} chars)")
        logger.info("🎉 E2E Fallback Flow PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"💥 E2E Test Failed with Exception: {e}", exc_info=True)
        return False
        
    finally:
        # Cleanup: Restore backup
        if backup_path.exists():
            shutil.move(backup_path, FALLBACK_TEMPLATE_FILE)
            logger.info("Restored original template file")
        elif FALLBACK_TEMPLATE_FILE.exists():
            # If we created it new, maybe leave it or delete? 
            # Better to leave it if it wasn't there, but user has it.
            # user has it committed.
            pass

if __name__ == "__main__":
    try:
        success = asyncio.run(test_fallback_e2e_flow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        sys.exit(1)

