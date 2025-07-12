import asyncio
import json
import logging
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)

class MCPExecutor:
    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = mcp_server_path
    
    async def execute_tool(self, tool_name: str, args: str) -> Any:
        """Execute a tool through the MCP server"""
        try:
            # Parse arguments if they're a string
            if isinstance(args, str):
                args_dict = json.loads(args)
            else:
                args_dict = args
            
            # Prepare the request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args_dict,
                },
                "id": 1,
            }
            
            # Run the MCP server as a subprocess
            process = await asyncio.create_subprocess_exec(
                'python', self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send request and get response
            stdout, stderr = await process.communicate(
                input=json.dumps(request).encode()
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"MCP process exited with code {process.returncode}: {error_msg}")
            
            # Parse response
            response = json.loads(stdout.decode())
            
            if "error" in response:
                raise Exception(f"MCP error: {response['error']['message']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"MCP executor error: {e}")
            raise