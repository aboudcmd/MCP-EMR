import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv

from fhir_client import FHIRClient
from types_models import (
    SearchPatientsArgs,
    GetPatientDetailsArgs,
    GetPatientConditionsArgs,
    GetPatientMedicationsArgs,
    GetPatientObservationsArgs,
    GetPatientEncountersArgs,
    GetPatientAllergiesArgs
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FHIR client
fhir_client = FHIRClient(
    base_url=os.getenv("FHIR_SERVER_URL", "http://10.201.205.101:8007/")
)

# Server state
initialized = False

async def execute_tool(tool_name: str, args: dict):
    """Execute a tool based on its name and arguments"""
    
    if tool_name == "search_patients":
        return await fhir_client.search_patients(SearchPatientsArgs(**args))
    
    elif tool_name == "get_patient_details":
        return await fhir_client.get_patient_details(args["patientId"])
    
    elif tool_name == "get_patient_conditions":
        return await fhir_client.get_patient_conditions(
            args["patientId"],
            args.get("clinicalStatus")
        )
    
    elif tool_name == "get_patient_medications":
        return await fhir_client.get_patient_medications(
            args["patientId"],
            args.get("status")
        )
    
    elif tool_name == "get_patient_observations":
        return await fhir_client.get_patient_observations(
            GetPatientObservationsArgs(**args)
        )
    
    elif tool_name == "get_patient_encounters":
        return await fhir_client.get_patient_encounters(
            GetPatientEncountersArgs(**args)
        )
    
    elif tool_name == "get_patient_allergies":
        return await fhir_client.get_patient_allergies(args["patientId"])
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

async def handle_request(request: dict) -> dict:
    """Handle a single JSON-RPC request"""
    global initialized
    
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            # Handle initialization
            initialized = True
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "emr-fhir-server",
                        "version": "1.0.0"
                    }
                },
                "id": request_id
            }
        
        elif method == "tools/call":
            # Handle tool calls
            if not initialized:
                raise Exception("Server not initialized")
            
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            
            result = await execute_tool(tool_name, tool_args)
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        
        else:
            raise Exception(f"Unknown method: {method}")
    
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": request.get("id")
        }

async def main():
    """Main entry point for the persistent MCP server"""
    logger.info("Starting MCP server...")
    
    try:
        # Read requests from stdin line by line
        while True:
            try:
                # Read a line from stdin
                line = sys.stdin.readline()
                if not line:
                    break  # EOF
                
                line = line.strip()
                if not line:
                    continue
                
                logger.info(f"Received request: {line[:100]}...")
                
                # Parse JSON request
                request = json.loads(line)
                
                # Handle the request
                response = await handle_request(request)
                
                # Send response
                response_json = json.dumps(response)
                print(response_json, flush=True)
                logger.info(f"Sent response: {response_json[:100]}...")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        logger.info("MCP server shutting down...")

if __name__ == "__main__":
    asyncio.run(main())