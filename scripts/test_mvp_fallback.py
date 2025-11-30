#!/usr/bin/env python3
"""
🚀 Jr Dev Agent - MVP Jira Fallback Flow Test Script
====================================================

This script demonstrates the MVP Jira Fallback Flow functionality.
It shows how the system gracefully falls back to local data when
the MCP server is unavailable.

Usage:
    python scripts/test_mvp_fallback.py
    
Author: Jr Dev Agent Team
Version: 1.0
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from jr_dev_agent.utils.load_ticket_metadata import (
    load_ticket_metadata,
    get_fallback_status,
    validate_ticket_metadata,
    JiraFallbackError
)

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n📋 {title}")
    print("-" * 50)

def print_success(message: str):
    """Print a success message"""
    print(f"✅ {message}")

def print_error(message: str):
    """Print an error message"""
    print(f"❌ {message}")

def print_info(message: str):
    """Print an info message"""
    print(f"ℹ️  {message}")

def test_fallback_status():
    """Test the fallback status functionality"""
    print_section("Testing Fallback Status")
    
    try:
        status = get_fallback_status()
        print_success("Retrieved fallback status successfully")
        
        print(f"   📄 Fallback file exists: {status['fallback_file_exists']}")
        print(f"   📂 Fallback file path: {status['fallback_file_path']}")
        print(f"   📊 File size: {status['fallback_file_size']} bytes")
        print(f"   🔧 Dev mode: {status['dev_mode']}")
        print(f"   🌐 Jira MCP URL: {status['jira_mcp_url']}")
        print(f"   ⏱️  Timeout: {status['jira_timeout']} seconds")
        
        if status['last_modified']:
            print(f"   📅 Last modified: {status['last_modified']}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to get fallback status: {e}")
        return False

def test_normal_flow():
    """Test the normal flow (will timeout and fall back)"""
    print_section("Testing Normal Flow (Expected to Fall Back)")
    
    ticket_id = "CEPG-67890"
    
    try:
        print_info(f"Attempting to load ticket: {ticket_id}")
        print_info("This will timeout and trigger fallback...")
        
        start_time = time.time()
        metadata = load_ticket_metadata(ticket_id)
        end_time = time.time()
        
        print_success(f"Loaded metadata in {end_time - start_time:.2f} seconds")
        
        # Check if fallback was used
        fallback_used = metadata.get("_fallback_used", False)
        if fallback_used:
            print_success("Fallback mechanism activated successfully")
            print(f"   📋 Template: {metadata.get('template_name')}")
            print(f"   📝 Summary: {metadata.get('summary')}")
            print(f"   🎯 Feature: {metadata.get('feature')}")
            print(f"   📊 Priority: {metadata.get('priority')}")
            print(f"   📁 Files affected: {len(metadata.get('files_affected', []))}")
            print(f"   ✅ Acceptance criteria: {len(metadata.get('acceptance_criteria', []))}")
            
            # Show fallback metadata
            print_info(f"Fallback timestamp: {metadata.get('_fallback_timestamp')}")
            print_info(f"Fallback file: {metadata.get('_fallback_file')}")
        else:
            print_error("Expected fallback to be used, but it wasn't")
            return False
            
        return True
        
    except Exception as e:
        print_error(f"Failed to load ticket metadata: {e}")
        return False

def test_dev_mode():
    """Test the dev mode functionality"""
    print_section("Testing Dev Mode (Forced Fallback)")
    
    # Set dev mode
    os.environ["DEV_MODE"] = "true"
    
    ticket_id = "CEPG-67890"
    
    try:
        print_info(f"Loading ticket in dev mode: {ticket_id}")
        print_info("This should use fallback immediately...")
        
        start_time = time.time()
        metadata = load_ticket_metadata(ticket_id)
        end_time = time.time()
        
        print_success(f"Loaded metadata in {end_time - start_time:.2f} seconds")
        
        # Check if fallback was used
        fallback_used = metadata.get("_fallback_used", False)
        if fallback_used:
            print_success("Dev mode fallback worked correctly")
            print(f"   📋 Template: {metadata.get('template_name')}")
            print(f"   📝 Summary: {metadata.get('summary')}")
        else:
            print_error("Expected fallback to be used in dev mode")
            return False
            
        return True
        
    except Exception as e:
        print_error(f"Failed to load ticket metadata in dev mode: {e}")
        return False
    finally:
        # Clean up
        if "DEV_MODE" in os.environ:
            del os.environ["DEV_MODE"]

def test_validation():
    """Test the metadata validation functionality"""
    print_section("Testing Metadata Validation")
    
    try:
        # Load metadata first
        metadata = load_ticket_metadata("CEPG-67890")
        
        # Validate it
        validated = validate_ticket_metadata(metadata)
        
        print_success("Metadata validation passed")
        print(f"   🎫 Ticket ID: {validated.ticket_id}")
        print(f"   📋 Template: {validated.template_name}")
        print(f"   📝 Summary: {validated.summary}")
        print(f"   🎯 Feature: {validated.feature}")
        print(f"   📊 Priority: {validated.priority}")
        print(f"   ⭐ Story points: {validated.story_points}")
        print(f"   🏷️  Labels: {', '.join(validated.labels)}")
        
        return True
        
    except Exception as e:
        print_error(f"Metadata validation failed: {e}")
        return False

def test_error_handling():
    """Test error handling scenarios"""
    print_section("Testing Error Handling")
    
    # Test with invalid ticket ID
    try:
        print_info("Testing with invalid ticket ID...")
        metadata = load_ticket_metadata("INVALID-123")
        print_error("Expected error for invalid ticket ID, but didn't get one")
        return False
        
    except ValueError as e:
        print_success(f"Correctly caught validation error: {e}")
        
    except Exception as e:
        print_success(f"Correctly caught error: {e}")
    
    # Test with empty ticket ID
    try:
        print_info("Testing with empty ticket ID...")
        metadata = load_ticket_metadata("")
        print_error("Expected error for empty ticket ID, but didn't get one")
        return False
        
    except ValueError as e:
        print_success(f"Correctly caught empty ticket ID error: {e}")
        
    except Exception as e:
        print_success(f"Correctly caught error: {e}")
    
    return True

def main():
    """Main test function"""
    print_header("Jr Dev Agent - MVP Jira Fallback Flow Test")
    
    print_info(f"Test started at: {datetime.now().isoformat()}")
    print_info(f"Python version: {sys.version}")
    print_info(f"Project root: {project_root}")
    
    # Run all tests
    tests = [
        ("Fallback Status", test_fallback_status),
        ("Normal Flow", test_normal_flow),
        ("Dev Mode", test_dev_mode),
        ("Validation", test_validation),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print_success(f"{test_name} test passed")
            else:
                print_error(f"{test_name} test failed")
                
        except Exception as e:
            print_error(f"{test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_section("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📊 Tests passed: {passed}/{total}")
    
    if passed == total:
        print_success("All tests passed! 🎉")
        print_info("The MVP Jira Fallback Flow is working correctly.")
    else:
        print_error(f"Some tests failed. Please review the output above.")
    
    # Show individual results
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print_header("Test Complete")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 