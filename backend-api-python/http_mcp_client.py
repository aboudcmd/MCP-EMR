"""HTTP-based MCP client for production microservices architecture"""
import logging
import httpx
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class HTTPMCPClient:
    """HTTP-based MCP client for microservices architecture"""
    
    def __init__(self, mcp_server_url: str):
        self.mcp_server_url = mcp_server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def execute_tool(self, tool_name: str, args: Any) -> Any:
        """Execute a tool through the HTTP MCP server"""
        try:
            # Parse arguments if they're a string
            if isinstance(args, str):
                import json
                args_dict = json.loads(args)
            else:
                args_dict = args
            
            logger.info("="*40)
            logger.info(f"HTTP MCP CLIENT: Calling MCP server")
            logger.info(f"Tool: {tool_name}")
            logger.info(f"Args: {args_dict}")
            logger.info(f"MCP Server URL: {self.mcp_server_url}")
            logger.info("="*40)
            
            # Make HTTP request to MCP server
            response = await self.client.post(
                f"{self.mcp_server_url}/execute_tool",
                json={
                    "tool_name": tool_name,
                    "args": args_dict
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get("success", False):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"MCP server returned error: {error_msg}")
                raise Exception(f"MCP error: {error_msg}")
            
            tool_result = result.get("result", {})
            
            # Log result summary (truncate for readability)
            result_str = str(tool_result)
            logger.info(f"✅ HTTP MCP CLIENT: Got response from MCP server")
            logger.info(f"Response type: {type(tool_result)}")
            if len(result_str) > 500:
                logger.info(f"Response preview: {result_str[:500]}...")
            else:
                logger.info(f"Response: {result_str}")
            
            return tool_result
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error executing tool {tool_name}: {e}")
            raise Exception(f"MCP server communication error: {e}")
        except Exception as e:
            logger.error(f"MCP client error for {tool_name}: {e}", exc_info=True)
            raise
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = await self.client.get(f"{self.mcp_server_url}/health")
            response.raise_for_status()
            health_data = response.json()
            return health_data.get("status") == "ok"
        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()