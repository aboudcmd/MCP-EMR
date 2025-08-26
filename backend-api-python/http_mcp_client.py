"""HTTP-based MCP client for production microservices architecture"""
import logging
import httpx
import asyncio
from typing import Any

logger = logging.getLogger(__name__)

class HTTPMCPClient:
    """Production-ready HTTP-based MCP client with per-request isolation"""
    
    def __init__(self, mcp_server_url: str):
        self.mcp_server_url = mcp_server_url.rstrip('/')
        # Client config for fresh clients per request - optimized for large JSON responses
        self._client_config = {
            "timeout": httpx.Timeout(60.0, read=120.0),  # Extended read timeout for large medical datasets  
            "transport": httpx.AsyncHTTPTransport(retries=3),
            "limits": httpx.Limits(max_connections=10, max_keepalive_connections=5),
            "headers": {
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",  # Enable compression for large responses
                "Connection": "close",  # Force connection close to prevent sharing issues
            },
        }
    
    async def _create_fresh_client(self) -> httpx.AsyncClient:
        """Create fresh HTTP client for each request to prevent connection sharing issues"""
        return httpx.AsyncClient(**self._client_config)
        
    async def execute_tool(self, tool_name: str, args: Any) -> Any:
        """Execute a tool through the HTTP MCP server with fresh client and retry logic"""
        # Parse arguments if they're a string
        if isinstance(args, str):
            import json
            args_dict = json.loads(args)
        else:
            args_dict = args
        
        # Retry logic for transient errors
        max_retries = 3
        retry_delay = 2.0  # seconds
        
        for attempt in range(max_retries):
            # Create fresh client for each request to avoid connection sharing issues
            async with await self._create_fresh_client() as client:
                try:
                    logger.info("="*40)
                    logger.info(f"HTTP MCP CLIENT: Calling MCP server (attempt {attempt + 1}/{max_retries})")
                    logger.info(f"Tool: {tool_name}")
                    logger.info(f"Args: {args_dict}")
                    logger.info(f"MCP Server URL: {self.mcp_server_url}")
                    logger.info("="*40)
                    
                    # Make HTTP request to MCP server
                    response = await client.post(
                        f"{self.mcp_server_url}/execute_tool",
                        json={
                            "tool_name": tool_name,
                            "args": args_dict
                        }
                    )
                    
                    logger.info(f"HTTP response status: {response.status_code}")
                    logger.info(f"Response content-length: {response.headers.get('content-length', 'unknown')}")
                    
                    response.raise_for_status()
                    
                    # Read response content safely for large JSON payloads
                    try:
                        # Use response.json() directly to avoid double text reading
                        result = response.json()
                        logger.info(f"✅ JSON parsed successfully for {tool_name}")
                        
                    except Exception as json_error:
                        logger.error(f"JSON parsing error for {tool_name}: {type(json_error).__name__} - {str(json_error)}")
                        try:
                            response_text = response.text
                            logger.error(f"Raw response length: {len(response_text)}")
                            if len(response_text) > 2000:
                                logger.error(f"Response preview: {response_text[:2000]}...")
                            else:
                                logger.error(f"Raw response: {response_text}")
                        except Exception as text_error:
                            logger.error(f"Could not read response text: {text_error}")
                        raise Exception(f"Failed to parse MCP server response: {type(json_error).__name__} - {str(json_error)}")
                    
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
                    
                except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                    # Network/connection errors - retry
                    logger.warning(f"Transient error on attempt {attempt + 1}/{max_retries} for {tool_name}: {type(e).__name__}: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                        continue
                    else:
                        logger.error(f"All retry attempts failed for {tool_name}")
                        raise Exception(f"MCP server communication error after {max_retries} attempts: {e}")
                        
                except httpx.HTTPStatusError as e:
                    # Server returned error status - don't retry
                    logger.error(f"HTTP status error executing tool {tool_name}: {e}")
                    raise Exception(f"MCP server returned error status: {e}")
                    
                except Exception as e:
                    # Other errors - don't retry
                    logger.error(f"MCP client error for {tool_name}: {e}", exc_info=True)
                    raise
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        async with await self._create_fresh_client() as client:
            try:
                response = await client.get(f"{self.mcp_server_url}/health")
                response.raise_for_status()
                health_data = response.json()
                return health_data.get("status") == "ok"
            except Exception as e:
                logger.error(f"MCP server health check failed: {e}", exc_info=True)
                return False
    
    async def close(self):
        """No-op for compatibility - clients are auto-closed with async context managers"""
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()