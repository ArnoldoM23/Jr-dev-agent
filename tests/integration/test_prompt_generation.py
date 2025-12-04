import sys
import os
import asyncio
import logging
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_test")

from jr_dev_agent.services.prompt_builder import PromptBuilder

async def test_prompt_generation_robustness():
    logger.info("🧪 Starting PromptBuilder robustness integration test...")
    
    builder = PromptBuilder()
    await builder.initialize()
    
    # 1. Test Case: Labels containing dictionaries (The likely crash cause)
    logger.info("Test Case 1: Labels as list of dicts")
    ticket_data_bad_labels = {
        "ticket_id": "TEST-1",
        "summary": "Test Ticket",
        "description": "Description",
        "labels": [{"name": "feature"}, {"name": "urgent"}],  # BAD DATA
        "components": ["backend"],
        "files_affected": ["src/main.py"]
    }
    
    try:
        prompt = await builder.generate_prompt("feature", ticket_data_bad_labels)
        logger.info("✅ Test Case 1 PASSED: Generated prompt despite bad labels")
        # Verify output contains stringified dict
        if "{'name': 'feature'}" in prompt:
            logger.info("   Verified dict was stringified in prompt")
    except Exception as e:
        logger.error(f"❌ Test Case 1 FAILED: {str(e)}")
        return False

    # 2. Test Case: Related Files as list of dicts (Synthetic Memory edge case)
    logger.info("Test Case 2: Related Files as list of dicts")
    ticket_data_clean = {
        "ticket_id": "TEST-2",
        "summary": "Test Ticket",
        "description": "Description",
        "labels": ["feature"],
        "components": ["backend"]
    }
    
    enrichment_data_bad = {
        "context_enriched": True,
        "complexity_score": 0.8,
        "related_files": [{"file": "a.ts"}, {"file": "b.ts"}], # BAD DATA
        "related_tickets": [{"id": "REL-1"}] # BAD DATA
    }
    
    try:
        prompt = await builder.generate_prompt("feature", ticket_data_clean, enrichment_data_bad)
        logger.info("✅ Test Case 2 PASSED: Generated prompt despite bad enrichment data")
        if "{'file': 'a.ts'}" in prompt:
            logger.info("   Verified related files were stringified")
    except Exception as e:
        logger.error(f"❌ Test Case 2 FAILED: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_prompt_generation_robustness())
        if success:
            print("\n✨ ALL INTEGRATION TESTS PASSED")
            sys.exit(0)
        else:
            print("\n💥 INTEGRATION TESTS FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        sys.exit(1)

