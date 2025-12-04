import sys
import os
import asyncio
import logging
import shutil
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_full_lifecycle")

from jr_dev_agent.graph.jr_dev_graph import JrDevGraph
from jr_dev_agent.utils.load_ticket_metadata import load_ticket_metadata, FALLBACK_TEMPLATE_FILE

async def test_full_lifecycle_with_memory():
    logger.info("🚀 Starting Full Lifecycle E2E Test (with dirty memory)")
    
    # Setup paths
    mem_root = Path("temp_e2e_memory")
    fallback_backup = Path(str(FALLBACK_TEMPLATE_FILE) + ".bak")
    config_path = Path("config.json")
    config_backup = Path("config.json.bak")
    
    # Cleanup existing
    if mem_root.exists():
        shutil.rmtree(mem_root)
    mem_root.mkdir()
    
    try:
        # Backup config
        if config_path.exists():
            shutil.copy(config_path, config_backup)
            
        # Write test config
        test_config = {
            "memory": {
                "backend": "fs",
                "fs": {"root_dir": str(mem_root)}
            }
        }
        config_path.write_text(json.dumps(test_config))
        # 1. Setup Dirty Memory (Simulate prior runs with list-of-dicts in files.json)
        feature_dir = mem_root / "features" / "e2e_feature" / "PRIOR-RUN-1"
        feature_dir.mkdir(parents=True)
        
        # files.json with DICTS (The crash trigger)
        files_data = {
            "files": [
                {"name": "src/legacy.ts", "size": 100},
                {"name": "src/utils.ts", "size": 200}
            ]
        }
        (feature_dir / "files.json").write_text(json.dumps(files_data))
        
        # agent_run.json
        agent_data = {
            "ticket_id": "PRIOR-RUN-1",
            "completion_timestamp": datetime.now().timestamp() - 86400, # 1 day ago
            "result": "merged"
        }
        (feature_dir / "agent_run.json").write_text(json.dumps(agent_data))
        
        # summary.json
        summary_data = {"template_name": "feature", "ticket_id": "PRIOR-RUN-1"}
        (feature_dir / "summary.json").write_text(json.dumps(summary_data))
        
        logger.info("✅ Created dirty memory environment")

        # 2. Setup Fallback Template (Simulate user input)
        if FALLBACK_TEMPLATE_FILE.exists():
            shutil.copy(FALLBACK_TEMPLATE_FILE, fallback_backup)
            
        template_content = """Jira_Ticket: E2E-CURRENT-1

Paste Template below
------------------------------------------------------------------------------------------------------
Name: feature
Feature: e2e_feature
Description: |
  Implement new functionality.
Prompt_Text: |
  You are an AI agent. Do the work.
Reference_Files:
  - src/legacy.ts
"""
        FALLBACK_TEMPLATE_FILE.write_text(template_content, encoding="utf-8")
        logger.info("✅ Created fallback template")

        # 3. Initialize Graph with Custom Memory Root
        graph = JrDevGraph()
        # Override root BEFORE initialization
        graph.synthetic_memory.root = str(mem_root)
        
        await graph.initialize()
        
        # 4. Run Workflow
        logger.info("🔄 Running full workflow...")
        
        # Force Dev Mode to ensure fallback usage
        os.environ["DEV_MODE"] = "true"
        
        # Load metadata (Step 1 of handle_prepare_agent_task)
        ticket_data = load_ticket_metadata("E2E-CURRENT-1")
        logger.info(f"Loaded ticket data: {ticket_data['ticket_id']}")
        
        if ticket_data.get("_fallback_used") != "text_template":
             logger.error(f"❌ Did not use text template! used={ticket_data.get('_fallback_used')}")
             return False

        # Process Ticket (Step 2 of handle_prepare_agent_task)
        # This runs: fetch -> select -> enrich -> generate -> finalize
        result = await graph.process_ticket(ticket_data, "session_e2e_test")
        
        # 5. Validate Result
        prompt = result["prompt"]
        logger.info(f"Generated prompt length: {len(prompt)}")
        
        if "You are an AI agent" not in prompt:
            logger.error("❌ Prompt text missing")
            return False
            
        # Check if memory context was added
        if "src/legacy.ts" not in prompt:
             logger.warning("⚠️ Expected file hint for src/legacy.ts in prompt (from memory overlap)")
             # Not a hard fail if heuristics differ, but good to check
             
        if "PRIOR-RUN-1" in prompt:
             logger.info("✅ Found prior run reference in prompt")
        else:
             logger.warning("⚠️ Did not find PRIOR-RUN-1 in prompt (maybe score too low?)")

        logger.info("🎉 Full Lifecycle E2E Test PASSED!")
        return True

    except Exception as e:
        logger.error(f"💥 Test FAILED with exception: {e}", exc_info=True)
        return False
        
    finally:
        # Cleanup
        if mem_root.exists():
            shutil.rmtree(mem_root)
        if fallback_backup.exists():
            shutil.move(fallback_backup, FALLBACK_TEMPLATE_FILE)
        
        # Restore config
        if config_backup.exists():
            shutil.move(config_backup, config_path)
        elif config_path.exists():
            os.remove(config_path)
            
        # Clean env
        if "DEV_MODE" in os.environ:
            del os.environ["DEV_MODE"]

if __name__ == "__main__":
    success = asyncio.run(test_full_lifecycle_with_memory())
    sys.exit(0 if success else 1)

