import sys
import os
import asyncio
import logging
import shutil
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_memory_crash")

from jr_dev_agent.services.synthetic_memory import SyntheticMemory
from jr_dev_agent.services.prompt_composer import PromptComposer

async def test_memory_crash():
    logger.info("🧪 Starting Memory Enrichment Crash Reproduction Test")
    
    # Setup dummy memory
    mem_root = Path("temp_test_memory")
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    try:
        # Create a feature with a prior run
        feature_dir = mem_root / "features" / "test_feature" / "PRIOR-1"
        feature_dir.mkdir(parents=True)
        
        # files.json with DICTS (this caused the crash)
        files_data = {
            "files": [
                {"name": "src/bad_file.ts", "size": 100},
                {"name": "src/good_file.ts", "size": 200}
            ]
        }
        (feature_dir / "files.json").write_text(json.dumps(files_data))
        
        # agent_run.json
        agent_data = {
            "ticket_id": "PRIOR-1",
            "completion_timestamp": 1700000000
        }
        (feature_dir / "agent_run.json").write_text(json.dumps(agent_data))
        
        # summary.json
        summary_data = {"template_name": "feature"}
        (feature_dir / "summary.json").write_text(json.dumps(summary_data))
        
        # Initialize services
        memory = SyntheticMemory(root=str(mem_root))
        composer = PromptComposer()
        
        # Ticket that matches the prior run feature scope
        ticket_data = {
            "ticket_id": "CURRENT-1",
            "summary": "Test feature task",
            "description": "implement test_feature",
            "feature": "test_feature",
            "files_affected": ["src/bad_file.ts"] # Overlap to trigger relevance
        }
        
        # 1. Test Enrichment (where _score_and_select runs)
        logger.info("Step 1: Enriching context...")
        enrichment = await memory.enrich_context(ticket_data)
        
        if not enrichment.get("context_enriched"):
            logger.error(f"❌ Enrichment failed: {enrichment.get('error')}")
            return False
            
        prior_runs = enrichment["memory_envelope"].get("prior_runs", [])
        if not prior_runs:
            logger.error("❌ No prior runs found (expected PRIOR-1)")
            return False
            
        # Verify files_touched is list of strings
        files_touched = prior_runs[0]["files_touched"]
        logger.info(f"Files touched in prior run: {files_touched}")
        
        if not all(isinstance(f, str) for f in files_touched):
            logger.error(f"❌ files_touched contains non-strings: {files_touched}")
            return False
            
        # 2. Test Prompt Composition (where join() crashed)
        logger.info("Step 2: Composing prompt...")
        try:
            prompt = composer.compose_final_prompt(
                "Base prompt", 
                enrichment["memory_envelope"], 
                ["src/file.ts"]
            )
            logger.info("✅ Prompt composed successfully")
        except TypeError as e:
            logger.error(f"❌ Prompt composition CRASHED: {e}")
            return False
            
        logger.info("🎉 Memory Enrichment Crash Test PASSED!")
        return True
        
    finally:
        if mem_root.exists():
            shutil.rmtree(mem_root)

if __name__ == "__main__":
    asyncio.run(test_memory_crash())

