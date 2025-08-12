# backend-api-python/mcp_executor.py
import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class PersistentMCPExecutor:
    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = mcp_server_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self._lock = asyncio.Lock()
        
    async def start(self):
        """Start the persistent MCP server process"""
        if self.process is not None:
            return
            
        try:
            # Start the MCP server as a persistent process
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(self.mcp_server_path)
            )
            
            logger.info(f"Started persistent MCP server with PID {self.process.pid}")
            
            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "emr-chatbot",
                        "version": "1.0.0"
                    }
                },
                "id": self._get_next_id()
            }
            
            await self._send_request(init_request)
            logger.info("MCP server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the persistent MCP server process"""
        if self.process is not None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")
            finally:
                self.process = None
                logger.info("MCP server stopped")
    
    def _get_next_id(self):
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, request: Dict) -> Dict:
        """Send a request to the MCP server and get response"""
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise Exception("MCP server not started or communication failed")
        
        try:
            # Send request
            request_data = json.dumps(request) + '\n'
            self.process.stdin.write(request_data.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise Exception("No response from MCP server")
            
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                logger.error(f"MCP returned error: {response['error']}")
                raise Exception(f"MCP error: {response['error'].get('message', 'Unknown error')}")
            
            return response
            
        except Exception as e:
            logger.error(f"MCP communication error: {e}")
            # Try to restart the server on communication failure
            await self.stop()
            raise
    
    async def execute_tool(self, tool_name: str, args: Any) -> Any:
        """Execute a tool through the persistent MCP server"""
        async with self._lock:
            try:
                # Ensure server is running
                if self.process is None:
                    await self.start()
                
                # Parse arguments if they're a string
                if isinstance(args, str):
                    args_dict = json.loads(args)
                else:
                    args_dict = args
                
                logger.info(f"Executing tool {tool_name} with args: {args_dict}")
                
                # Prepare the tool call request
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": args_dict,
                    },
                    "id": self._get_next_id(),
                }
                
                # Send request and get response
                response = await self._send_request(request)
                result = response.get("result", {})
                
                # Log result summary (truncate for readability)
                result_str = json.dumps(result)
                if len(result_str) > 500:
                    logger.info(f"Tool {tool_name} returned: {result_str[:500]}...")
                else:
                    logger.info(f"Tool {tool_name} returned: {result_str}")
                
                return result
                
            except Exception as e:
                logger.error(f"MCP executor error for {tool_name}: {e}", exc_info=True)
                # Try to restart server on error
                await self.stop()
                raise
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

# Backward compatibility alias
MCPExecutor = PersistentMCPExecutor