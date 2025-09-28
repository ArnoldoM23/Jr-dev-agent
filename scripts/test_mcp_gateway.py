#!/usr/bin/env python3
"""
Test MCP Gateway Implementation

This script tests the MCP (Model Context Protocol) gateway endpoints to ensure
they work correctly with the existing Jr Dev Agent infrastructure.

Usage:
    python scripts/test_mcp_gateway.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TICKET_ID = "CEPG-67890"  # Using the existing fallback ticket


class MCPGatewayTester:
    """Test suite for MCP Gateway functionality"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_server_health(self) -> bool:
        """Test basic server health"""
        logger.info("🔍 Testing server health...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Server healthy: {health_data['status']}")
                    return True
                else:
                    logger.error(f"❌ Server unhealthy: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    async def test_mcp_initialization(self) -> bool:
        """Test MCP initialization handshake"""
        logger.info("🔍 Testing MCP initialization...")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": "test-init-1"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/mcp/initialize",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        logger.info(f"✅ MCP initialization successful")
                        logger.info(f"   Protocol version: {result['result']['protocolVersion']}")
                        logger.info(f"   Server: {result['result']['serverInfo']['name']}")
                        return True
                    else:
                        logger.error(f"❌ MCP initialization failed: {result}")
                        return False
                else:
                    logger.error(f"❌ MCP initialization HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ MCP initialization exception: {e}")
            return False
    
    async def test_mcp_tools_list(self) -> bool:
        """Test MCP tools discovery"""
        logger.info("🔍 Testing MCP tools list...")
        
        payload = {
            "jsonrpc": "2.0", 
            "method": "tools/list",
            "id": "test-tools-1"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/mcp/tools/list",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        logger.info(f"✅ Found {len(tools)} MCP tools:")
                        for tool in tools:
                            logger.info(f"   - {tool['name']}: {tool['description']}")
                        return len(tools) > 0
                    else:
                        logger.error(f"❌ Tools list failed: {result}")
                        return False
                else:
                    logger.error(f"❌ Tools list HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Tools list exception: {e}")
            return False
    
    async def test_prepare_agent_task(self) -> tuple[bool, str]:
        """Test prepare_agent_task tool"""
        logger.info(f"🔍 Testing prepare_agent_task with ticket {TEST_TICKET_ID}...")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "prepare_agent_task",
                "arguments": {
                    "ticket_id": TEST_TICKET_ID,
                    "repo": "test-repo",
                    "branch": "feature/test"
                }
            },
            "id": "test-prepare-1"
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                duration = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        prompt_data = result["result"]
                        session_id = prompt_data.get("metadata", {}).get("session_id")
                        
                        logger.info(f"✅ prepare_agent_task successful ({duration:.2f}s)")
                        logger.info(f"   Session ID: {session_id}")
                        logger.info(f"   Template: {prompt_data.get('metadata', {}).get('template_used')}")
                        logger.info(f"   Files to modify: {len(prompt_data.get('metadata', {}).get('files_to_modify', []))}")
                        logger.info(f"   Commands: {prompt_data.get('metadata', {}).get('commands', [])}")
                        logger.info(f"   Prompt length: {len(prompt_data.get('prompt_text', ''))}")
                        
                        return True, session_id
                    else:
                        logger.error(f"❌ prepare_agent_task failed: {result}")
                        return False, None
                else:
                    logger.error(f"❌ prepare_agent_task HTTP error: {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text}")
                    return False, None
                    
        except Exception as e:
            logger.error(f"❌ prepare_agent_task exception: {e}")
            return False, None
    
    async def test_finalize_session(self, session_id: str) -> bool:
        """Test finalize_session tool"""
        if not session_id:
            logger.warning("⚠️ Skipping finalize_session test (no session ID)")
            return True
            
        logger.info(f"🔍 Testing finalize_session for {session_id}...")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call", 
            "params": {
                "name": "finalize_session",
                "arguments": {
                    "session_id": session_id,
                    "ticket_id": TEST_TICKET_ID,
                    "pr_url": "https://github.com/test/repo/pull/123",
                    "files_modified": [
                        "src/graphql/types/Order.graphql",
                        "src/graphql/inputs/OrderInput.graphql"
                    ],
                    "retry_count": 1,
                    "manual_edits": 0,
                    "duration_ms": 180000
                }
            },
            "id": "test-finalize-1"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        finalize_data = result["result"]
                        pess_score = finalize_data.get("pess_score", 0)
                        
                        logger.info(f"✅ finalize_session successful")
                        logger.info(f"   PESS Score: {pess_score}")
                        logger.info(f"   Analytics: {finalize_data.get('analytics', {}).keys()}")
                        
                        return True
                    else:
                        logger.error(f"❌ finalize_session failed: {result}")
                        return False
                else:
                    logger.error(f"❌ finalize_session HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ finalize_session exception: {e}")
            return False
    
    async def test_health_tool(self) -> bool:
        """Test health MCP tool"""
        logger.info("🔍 Testing health MCP tool...")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "health",
                "arguments": {}
            },
            "id": "test-health-1"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        health_data = result["result"]
                        status = health_data.get("status")
                        services = health_data.get("services", {})
                        
                        logger.info(f"✅ Health tool successful")
                        logger.info(f"   Status: {status}")
                        logger.info(f"   Services: {list(services.keys())}")
                        logger.info(f"   MCP tools available: {health_data.get('mcp_tools_available')}")
                        
                        return status == "healthy"
                    else:
                        logger.error(f"❌ Health tool failed: {result}")
                        return False
                else:
                    logger.error(f"❌ Health tool HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Health tool exception: {e}")
            return False
    
    async def run_full_test_suite(self) -> bool:
        """Run complete test suite"""
        logger.info("🚀 Starting MCP Gateway test suite...")
        
        test_results = []
        
        # Test 1: Server Health
        test_results.append(await self.test_server_health())
        
        # Test 2: MCP Initialization  
        test_results.append(await self.test_mcp_initialization())
        
        # Test 3: Tools Discovery
        test_results.append(await self.test_mcp_tools_list())
        
        # Test 4: Health Tool
        test_results.append(await self.test_health_tool())
        
        # Test 5: Prepare Agent Task
        prepare_success, session_id = await self.test_prepare_agent_task()
        test_results.append(prepare_success)
        
        # Test 6: Finalize Session (if we have session ID)
        test_results.append(await self.test_finalize_session(session_id))
        
        # Summary
        passed = sum(test_results)
        total = len(test_results)
        success_rate = passed / total * 100
        
        logger.info(f"\n📊 Test Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All MCP Gateway tests PASSED! Ready for MVP demo.")
            return True
        else:
            logger.error(f"❌ {total - passed} test(s) FAILED. Check implementation.")
            return False


async def main():
    """Main test execution"""
    print("=" * 60)
    print("🧪 Jr Dev Agent - MCP Gateway Test Suite")
    print("=" * 60)
    
    try:
        async with MCPGatewayTester() as tester:
            success = await tester.run_full_test_suite()
            
        if success:
            print("\n✅ MCP Gateway is ready for cross-IDE integration!")
            return 0
        else:
            print("\n❌ MCP Gateway has issues that need fixing.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user.")
        return 1
    except Exception as e:
        logger.error(f"💥 Test suite crashed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
