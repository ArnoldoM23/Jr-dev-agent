#!/usr/bin/env python3
"""
Start MCP Gateway Server

This script starts the Jr Dev Agent MCP Gateway server with proper configuration
for development and testing. It includes health checks and automatic fallback setup.

Usage:
    python scripts/start_mcp_gateway.py [--dev] [--port 8000]
"""

import argparse
import asyncio
import logging
import os
import sys
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPGatewayLauncher:
    """Launcher for the MCP Gateway server with proper setup and configuration"""
    
    def __init__(self):
        self.server = None
        self.should_shutdown = False
    
    def setup_environment(self, dev_mode: bool = False):
        """Setup environment variables and configuration"""
        logger.info("🔧 Setting up environment...")
        
        # Set development mode
        if dev_mode:
            os.environ["DEV_MODE"] = "true"
            os.environ["LOG_LEVEL"] = "DEBUG"
            logger.info("✅ Development mode enabled")
        
        # Ensure fallback file exists
        fallback_dir = project_root / "jr_dev_agent" / "fallback"
        fallback_file = fallback_dir / "jira_prompt.json"
        
        if not fallback_file.exists():
            logger.warning("⚠️ Fallback file missing - creating sample file...")
            self.create_sample_fallback_file(fallback_file)
        else:
            logger.info("✅ Fallback file found")
    
    def create_sample_fallback_file(self, fallback_file: Path):
        """Create sample fallback file for development"""
        import json
        
        fallback_file.parent.mkdir(parents=True, exist_ok=True)
        
        sample_data = {
            "ticket_id": "CEPG-67890",
            "template_name": "feature_schema_change",
            "summary": "Add pickup option to Order schema",
            "description": "Allow user to select store pickup for their order. This feature enables customers to choose pickup at a nearby store location instead of delivery, improving customer flexibility and reducing shipping costs.",
            "acceptance_criteria": [
                "Update OrderInput.graphql to include pickup_store_id field",
                "Update Order.graphql schema to include pickup_store and pickup_time fields",
                "Add validation for pickup_store_id when pickup option is selected",
                "Ensure pickup_time is within store operating hours",
                "Update GraphQL resolvers to handle pickup logic"
            ],
            "files_affected": [
                "src/graphql/types/Order.graphql",
                "src/graphql/inputs/OrderInput.graphql", 
                "src/graphql/resolvers/orderResolver.ts",
                "src/graphql/resolvers/orderInputResolver.ts"
            ],
            "feature": "order_self_pickup",
            "priority": "high",
            "story_points": 5,
            "labels": ["feature", "schema-change", "pickup", "customer-experience"],
            "component": "order-service",
            "assignee": "development-team",
            "reporter": "product-manager",
            "created_date": "2025-07-15T10:30:00Z",
            "updated_date": "2025-07-15T14:45:00Z",
            "epic_link": "CEPG-67000",
            "sprint": "Sprint 2025.3"
        }
        
        with open(fallback_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        logger.info(f"✅ Created sample fallback file: {fallback_file}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, shutting down...")
            self.should_shutdown = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_server(self, host: str, port: int, dev_mode: bool):
        """Run the MCP Gateway server"""
        logger.info(f"🚀 Starting MCP Gateway server on {host}:{port}")
        
        # Server configuration
        config = uvicorn.Config(
            "jr_dev_agent.server.main:app",
            host=host,
            port=port,
            log_level="debug" if dev_mode else "info",
            reload=dev_mode,
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # Start server
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"❌ Server failed to start: {e}")
            raise
    
    def print_banner(self, host: str, port: int, dev_mode: bool):
        """Print startup banner"""
        print("=" * 70, file=sys.stderr)
        print("🤖 Jr Dev Agent - MCP Gateway Server v2.0.0-MVP", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"🌐 Server URL: http://{host}:{port}", file=sys.stderr)
        print(f"📚 API Docs: http://{host}:{port}/docs", file=sys.stderr)
        print(f"🔧 Dev Mode: {'Enabled' if dev_mode else 'Disabled'}", file=sys.stderr)
        print(f"🔍 Health Check: http://{host}:{port}/health", file=sys.stderr)
        print("", file=sys.stderr)
        print("📋 Available Endpoints:", file=sys.stderr)
        print(f"   • Health: GET /health", file=sys.stderr)
        print(f"   • MCP Initialize: POST /mcp/initialize", file=sys.stderr)
        print(f"   • MCP Tools List: POST /mcp/tools/list", file=sys.stderr)
        print(f"   • MCP Tools Call: POST /mcp/tools/call", file=sys.stderr)
        print(f"   • Legacy v1 Endpoints: /api/*", file=sys.stderr)
        print("", file=sys.stderr)
        print("🧪 Test Command:", file=sys.stderr)
        print(f"   python scripts/test_mcp_gateway.py", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
    
    def print_shutdown_banner(self):
        """Print shutdown banner"""
        print("\n" + "=" * 50, file=sys.stderr)
        print("👋 Jr Dev Agent MCP Gateway Server Stopped", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
    
    async def launch(self, host: str = "0.0.0.0", port: int = 8000, dev_mode: bool = False):
        """Main launch method"""
        try:
            # Setup
            self.setup_environment(dev_mode)
            self.setup_signal_handlers()
            
            # Print banner
            self.print_banner(host, port, dev_mode)
            
            # Start server
            await self.run_server(host, port, dev_mode)
            
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
        except Exception as e:
            logger.error(f"💥 Server crashed: {e}")
            raise
        finally:
            self.print_shutdown_banner()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Start Jr Dev Agent MCP Gateway Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode with auto-reload and debug logging"
    )
    
    args = parser.parse_args()
    
    # Launch server
    launcher = MCPGatewayLauncher()
    asyncio.run(launcher.launch(args.host, args.port, args.dev))


if __name__ == "__main__":
    main()
