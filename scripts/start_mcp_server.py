#!/usr/bin/env python3
"""
Start LangGraph MCP Server

This script starts the Jr Dev Agent MCP server for development and testing.
"""

import os
import sys
import asyncio
import uvicorn
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main function to start the MCP server"""
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
    
    print("🚀 Starting Jr Dev Agent MCP Server...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🔧 Dev Mode: {dev_mode}")
    print(f"📁 Project Root: {project_root}")
    print()
    
    # Set environment variables
    os.environ["DEV_MODE"] = "true" if dev_mode else "false"
    os.environ["PYTHONPATH"] = str(project_root)
    
    try:
        # Start the server
        uvicorn.run(
            "langgraph_mcp.server.main:app",
            host=host,
            port=port,
            reload=dev_mode,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 