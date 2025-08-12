#!/usr/bin/env python3
"""Test MCP tool execution pipeline"""
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add paths
sys.path.append(str(Path(__file__).parent / "backend-api-python"))
sys.path.append(str(Path(__file__).parent / "mcp-server-python"))

from mcp_executor import PersistentMCPExecutor

# Load environment variables
load_dotenv()

async def test_mcp_tools():
    """Test MCP tool execution"""
    
    mcp_server_path = str(Path(__file__).parent / "mcp-server-python" / "main.py")
    print(f"MCP server path: {mcp_server_path}")
    
    mcp_executor = PersistentMCPExecutor(
        mcp_server_path=mcp_server_path
    )
    
    try:
        # Start the executor
        await mcp_executor.start()
        print("[OK] MCP executor started")
        
        # Test get_patient_observations
        print("\n=== Testing get_patient_observations ===")
        patient_id = "416768"
        args = {"patientId": patient_id}
        
        result = await mcp_executor.execute_tool("get_patient_observations", args)
        print(f"Tool result type: {type(result)}")
        print(f"Tool result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and 'observations' in result:
            obs_count = len(result['observations'])
            total = result.get('total', 'unknown')
            print(f"[OK] Retrieved {obs_count} observations (total: {total})")
            
            if obs_count > 0:
                print("First observation:")
                first_obs = result['observations'][0]
                print(f"  - Type: {first_obs.get('type', 'Unknown')}")
                print(f"  - Value: {first_obs.get('value', 'No value')}")
                print(f"  - Date: {first_obs.get('effectiveDateTime', 'No date')}")
        else:
            print(f"[ERROR] Unexpected result format: {result}")
        
        # Test patient details for comparison
        print(f"\n=== Testing get_patient_details ===")
        patient_result = await mcp_executor.execute_tool("get_patient_details", {"patientId": patient_id})
        print(f"Patient: {patient_result.get('name', 'Unknown')} (ID: {patient_result.get('id', 'Unknown')})")
    
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await mcp_executor.stop()
        print("[OK] MCP executor stopped")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())