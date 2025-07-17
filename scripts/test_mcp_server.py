#!/usr/bin/env python3
"""
Test LangGraph MCP Server

This script tests the Jr Dev Agent MCP server endpoints to ensure they work correctly.
"""

import os
import sys
import asyncio
import aiohttp
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TICKET_ID = "CEPG-67890"

async def test_health_endpoint():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data['status']}")
                    print(f"📊 Services: {data['services']}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

async def test_ticket_endpoint():
    """Test the ticket metadata endpoint"""
    print(f"🎫 Testing ticket endpoint with {TEST_TICKET_ID}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/ticket/{TEST_TICKET_ID}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Ticket metadata retrieved successfully")
                    print(f"📋 Summary: {data.get('summary', 'N/A')}")
                    print(f"🔄 Source: {data.get('source', 'N/A')}")
                    print(f"📝 Template: {data.get('template_name', 'N/A')}")
                    return True
                else:
                    print(f"❌ Ticket endpoint failed: {response.status}")
                    text = await response.text()
                    print(f"📄 Response: {text}")
                    return False
    except Exception as e:
        print(f"❌ Ticket endpoint error: {e}")
        return False

async def test_prompt_generation():
    """Test the prompt generation endpoint"""
    print(f"🤖 Testing prompt generation for {TEST_TICKET_ID}...")
    
    # First get ticket data
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/ticket/{TEST_TICKET_ID}") as response:
                if response.status != 200:
                    print("❌ Failed to get ticket data for prompt generation")
                    return False
                
                ticket_data = await response.json()
                
                # Now test prompt generation
                prompt_request = {
                    "ticket_data": ticket_data,
                    "options": {
                        "include_context": True
                    }
                }
                
                async with session.post(
                    f"{BASE_URL}/api/prompt/generate",
                    json=prompt_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Prompt generated successfully")
                        print(f"📏 Prompt length: {len(data.get('prompt', ''))} characters")
                        print(f"🔑 Hash: {data.get('hash', 'N/A')}")
                        print(f"📋 Template used: {data.get('template_used', 'N/A')}")
                        print(f"📊 Processing time: {data.get('processing_info', {}).get('processing_time_ms', 'N/A')}ms")
                        return True
                    else:
                        print(f"❌ Prompt generation failed: {response.status}")
                        text = await response.text()
                        print(f"📄 Response: {text}")
                        return False
                        
    except Exception as e:
        print(f"❌ Prompt generation error: {e}")
        return False

async def test_debug_endpoints():
    """Test the debug endpoints (dev mode only)"""
    print("🔍 Testing debug endpoints...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test debug health
            async with session.get(f"{BASE_URL}/api/debug/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Debug health endpoint works")
                    print(f"🧠 LangGraph status: {data.get('langgraph', {}).get('status', 'N/A')}")
                elif response.status == 404:
                    print("ℹ️  Debug endpoints disabled (not in dev mode)")
                else:
                    print(f"⚠️  Debug health endpoint returned: {response.status}")
            
            # Test debug sessions
            async with session.get(f"{BASE_URL}/api/debug/sessions") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Debug sessions endpoint works")
                    print(f"📊 Active sessions: {len(data)}")
                elif response.status == 404:
                    print("ℹ️  Debug sessions disabled (not in dev mode)")
                else:
                    print(f"⚠️  Debug sessions endpoint returned: {response.status}")
                    
            return True
                    
    except Exception as e:
        print(f"❌ Debug endpoints error: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Jr Dev Agent MCP Server Test Suite")
    print("=" * 50)
    
    # Set dev mode for testing
    os.environ["DEV_MODE"] = "true"
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Ticket Metadata", test_ticket_endpoint),
        ("Prompt Generation", test_prompt_generation),
        ("Debug Endpoints", test_debug_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 30)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MCP server is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1) 