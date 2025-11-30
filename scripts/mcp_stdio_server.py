#!/usr/bin/env python3
"""
MCP STDIO Server for Jr Dev Agent

This script implements a proper MCP server using STDIO protocol,
allowing IDE clients (like Cursor) to communicate with a running
MCP gateway server.

The STDIO server acts as a bridge between the IDE and the HTTP-based
MCP gateway that must already be running.

Usage:
    This script is called automatically by the IDE via .cursor/mcp.json
    It expects the MCP gateway to be running on http://127.0.0.1:8000
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import httpx

# Configure logging to stderr (STDOUT is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# MCP Gateway URL (should be running separately)
MCP_GATEWAY_URL = "http://127.0.0.1:8000"


class MCPStdioServer:
    """STDIO-based MCP server that bridges to HTTP gateway"""
    
    def __init__(self, gateway_url: str = MCP_GATEWAY_URL):
        self.gateway_url = gateway_url
        self.client = None
        
    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"MCP STDIO Server initialized, connecting to {self.gateway_url}")
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.aclose()
            
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request and forward to HTTP gateway
        
        Args:
            request: MCP JSON-RPC request
            
        Returns:
            MCP JSON-RPC response
        """
        try:
            method = request.get("method")
            request_id = request.get("id")
            
            logger.info(f"Handling MCP request: {method} (id={request_id})")
            
            # Route to appropriate handler
            if method == "initialize":
                return await self.handle_initialize(request)
            elif method == "notifications/initialized":
                # Client confirmation of initialization - no response needed
                logger.info("Received notifications/initialized, ignoring")
                return None
            elif method == "tools/list":
                return await self.handle_tools_list(request)
            elif method == "tools/call":
                return await self.handle_tools_call(request)
            elif method == "prompts/list":
                return await self.handle_prompts_list(request)
            elif method == "prompts/get":
                return await self.handle_prompts_get(request)
            else:
                # Do not reply to unknown notifications (no id)
                if request_id is None:
                    logger.warning(f"Ignoring unknown notification: {method}")
                    return None
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        try:
            response = await self.client.post(
                f"{self.gateway_url}/mcp/initialize",
                json=request
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Initialize request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Gateway unreachable. Please start the MCP gateway server first: python scripts/start_mcp_gateway.py"
                }
            }
    
    async def handle_tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        try:
            response = await self.client.post(
                f"{self.gateway_url}/mcp/tools/list",
                json=request
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Tools list request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Gateway unreachable: {str(e)}"
                }
            }
    
    async def handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools/call request
        
        Pass through the response from the gateway without modification.
        The gateway already includes proper chat_injection field for IDEs.
        """
        try:
            response = await self.client.post(
                f"{self.gateway_url}/mcp/tools/call",
                json=request
            )
            response.raise_for_status()
            result = response.json()
            
            # Pass through the result as-is
            # The gateway already includes chat_injection field with proper format
            return result
            
        except Exception as e:
            logger.error(f"Tools call request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Gateway error: {str(e)}"
                }
            }
    
    async def handle_prompts_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        try:
            response = await self.client.post(
                f"{self.gateway_url}/mcp/prompts/list",
                json=request
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prompts list request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Gateway unreachable: {str(e)}"
                }
            }

    async def handle_prompts_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        try:
            response = await self.client.post(
                f"{self.gateway_url}/mcp/prompts/get",
                json=request
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prompts get request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Gateway unreachable: {str(e)}"
                }
            }

    async def run(self):
        """Run the STDIO server loop"""
        await self.initialize()
        
        logger.info("MCP STDIO Server started, reading from STDIN...")
        
        try:
            # Read JSON-RPC requests from STDIN line by line
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    # EOF reached
                    logger.info("STDIN closed, shutting down...")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)
                    
                    # Handle request
                    response = await self.handle_request(request)
                    
                    # Write JSON-RPC response to STDOUT (only if response is generated)
                    if response is not None:
                        response_line = json.dumps(response)
                        sys.stdout.write(response_line + "\n")
                        sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {line}, error: {str(e)}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()
                    
        except KeyboardInterrupt:
            logger.info("Interrupted, shutting down...")
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    server = MCPStdioServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

