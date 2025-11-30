#!/usr/bin/env python3
"""
MCP Setup Verification Script

This script verifies that your MCP setup is correct and ready to use.
Run this before using @jrdev commands in Cursor.

Usage:
    python scripts/verify_mcp_setup.py
"""

import sys
import json
import requests
from pathlib import Path

def print_status(message, status="info"):
    """Print colored status message"""
    colors = {
        "success": "\033[92m✅",
        "error": "\033[91m❌",
        "warning": "\033[93m⚠️ ",
        "info": "\033[94mℹ️ "
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')} {message}{reset}")


def check_gateway_running():
    """Check if MCP gateway is running"""
    print("\n🔍 Checking MCP Gateway...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print_status(f"Gateway is running (version: {data.get('version', 'unknown')})", "success")
            print_status(f"  Status: {data.get('status', 'unknown')}", "info")
            
            services = data.get("services", {})
            for service, status in services.items():
                print_status(f"  {service}: {status}", "info")
            
            return True
        else:
            print_status(f"Gateway returned status {response.status_code}", "error")
            return False
            
    except requests.exceptions.ConnectionError:
        print_status("Gateway is NOT running", "error")
        print_status("  Start it with: python scripts/start_mcp_gateway.py", "warning")
        return False
    except Exception as e:
        print_status(f"Error checking gateway: {str(e)}", "error")
        return False


def check_stdio_bridge():
    """Check if STDIO bridge script exists and is executable"""
    print("\n🔍 Checking STDIO Bridge...")
    
    bridge_path = Path("scripts/mcp_stdio_server.py")
    
    if not bridge_path.exists():
        print_status("STDIO bridge script not found", "error")
        return False
    
    print_status("STDIO bridge script exists", "success")
    
    if not bridge_path.stat().st_mode & 0o111:
        print_status("  Warning: Script is not executable", "warning")
        print_status("  Run: chmod +x scripts/mcp_stdio_server.py", "info")
    
    return True


def check_cursor_config():
    """Check if Cursor MCP config is correct"""
    print("\n🔍 Checking Cursor Configuration...")
    
    config_path = Path(".cursor/mcp.json")
    
    if not config_path.exists():
        print_status("Cursor config not found", "error")
        return False
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        if "mcpServers" not in config:
            print_status("Invalid config structure", "error")
            return False
        
        if "jrdev" not in config["mcpServers"]:
            print_status("'jrdev' server not configured", "error")
            return False
        
        jrdev_config = config["mcpServers"]["jrdev"]
        
        # Check if using STDIO bridge (correct) vs server (incorrect)
        args = jrdev_config.get("args", [])
        if any("mcp_stdio_server.py" in arg for arg in args):
            print_status("Config is using STDIO bridge (correct!)", "success")
        elif any("start_mcp_gateway.py" in arg for arg in args):
            print_status("Config is starting gateway server (INCORRECT!)", "error")
            print_status("  Update .cursor/mcp.json to use mcp_stdio_server.py", "warning")
            return False
        else:
            print_status("Unable to determine config type", "warning")
        
        return True
        
    except json.JSONDecodeError:
        print_status("Invalid JSON in config file", "error")
        return False
    except Exception as e:
        print_status(f"Error reading config: {str(e)}", "error")
        return False


def check_venv():
    """Check if virtual environment is activated"""
    print("\n🔍 Checking Python Environment...")
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_status("Virtual environment is activated", "success")
        print_status(f"  Python: {sys.executable}", "info")
        return True
    else:
        print_status("Virtual environment not activated", "warning")
        print_status("  Activate it with: source .venv/bin/activate", "info")
        return False


def test_prepare_agent_task():
    """Test the prepare_agent_task endpoint"""
    print("\n🔍 Testing prepare_agent_task...")
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": "verify-test",
            "params": {
                "name": "prepare_agent_task",
                "arguments": {
                    "ticket_id": "CEPG-67890"
                }
            }
        }
        
        response = requests.post(
            "http://127.0.0.1:8000/mcp/tools/call",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "error" in data and data["error"]:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                print_status(f"Tool returned error: {error_msg}", "error")
                return False
            
            result = data.get("result")
            if not result:
                print_status("No result in response", "error")
                return False
            
            # Check for CallToolResult structure (v2)
            has_content = "content" in result
            
            # Access metadata from _meta if present (v2) or root (v1 fallback)
            meta = result.get("_meta", result)
            
            has_prompt = "prompt_text" in meta
            has_chat_injection = "chat_injection" in meta
            has_metadata = "metadata" in meta
            
            print_status("prepare_agent_task works!", "success")
            print_status(f"  Has content array: {has_content}", "success" if has_content else "error")
            print_status(f"  Has prompt_text: {has_prompt}", "success" if has_prompt else "error")
            print_status(f"  Has chat_injection: {has_chat_injection}", "success" if has_chat_injection else "error")
            print_status(f"  Has metadata: {has_metadata}", "success" if has_metadata else "error")
            
            if has_chat_injection:
                chat_inj = meta["chat_injection"]
                enabled = chat_inj.get("enabled", False)
                has_message = "message" in chat_inj
                print_status(f"  chat_injection.enabled: {enabled}", "success" if enabled else "warning")
                print_status(f"  chat_injection has message: {has_message}", "success" if has_message else "error")
            
            return has_prompt and has_chat_injection
        else:
            print_status(f"Request failed with status {response.status_code}", "error")
            return False
            
    except Exception as e:
        print_status(f"Test failed: {str(e)}", "error")
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("🤖 Jr Dev Agent MCP Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Virtual Environment", check_venv),
        ("MCP Gateway", check_gateway_running),
        ("STDIO Bridge", check_stdio_bridge),
        ("Cursor Config", check_cursor_config),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # Only test endpoint if gateway is running
    if results["MCP Gateway"]:
        results["prepare_agent_task"] = test_prepare_agent_task()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "success" if passed else "error"
        print_status(f"{name}: {'PASS' if passed else 'FAIL'}", status)
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print_status("✨ All checks passed! You're ready to use @jrdev in Cursor!", "success")
        print("\nNext steps:")
        print("  1. Open Cursor")
        print("  2. Type: @jrdev prepare_agent_task CEPG-67890")
        print("  3. Prompt should appear in your chat input box")
        print("  4. Press Enter to execute!")
    else:
        print_status("❌ Some checks failed. Fix the issues above before using @jrdev.", "error")
        print("\nCommon fixes:")
        print("  • Gateway not running? → python scripts/start_mcp_gateway.py")
        print("  • Wrong config? → Check .cursor/mcp.json uses mcp_stdio_server.py")
        print("  • No venv? → source .venv/bin/activate")
    
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

