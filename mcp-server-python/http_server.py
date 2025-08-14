"""HTTP-based MCP server for production deployment"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

from fhir_client import FHIRClient
from types_models import (
    SearchPatientsArgs,
    GetPatientObservationsArgs,
    GetPatientEncountersArgs
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="EMR MCP Server", version="1.0.0")

# Initialize FHIR client
fhir_client = FHIRClient(
    base_url=os.getenv("FHIR_SERVER_URL", "http://10.201.205.101:8007/"),
    auth_token=os.getenv("FHIR_AUTH_TOKEN"),
    username=os.getenv("FHIR_USERNAME"),
    password=os.getenv("FHIR_PASSWORD")
)

class ToolRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]

class ToolResponse(BaseModel):
    success: bool
    result: Any = None
    error: str = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "mcp-server"}

@app.post("/execute_tool", response_model=ToolResponse)
async def execute_tool_endpoint(request: ToolRequest):
    """Execute a tool via HTTP"""
    try:
        logger.info(f"Executing tool {request.tool_name} with args: {request.args}")
        
        result = await execute_tool(request.tool_name, request.args)
        
        logger.info(f"Tool {request.tool_name} executed successfully")
        return ToolResponse(success=True, result=result)
        
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {e}", exc_info=True)
        return ToolResponse(success=False, error=str(e))

async def execute_tool(tool_name: str, args: dict):
    """Execute a tool based on its name and arguments"""
    
    try:
        logger.info(f"Executing tool {tool_name} with args: {args}")
        
        if tool_name == "search_patients":
            result = await fhir_client.search_patients(SearchPatientsArgs(**args))
        
        elif tool_name == "get_patient_details":
            result = await fhir_client.get_patient_details(args["patientId"])
        
        elif tool_name == "get_patient_conditions":
            result = await fhir_client.get_patient_conditions(
                args["patientId"],
                args.get("clinicalStatus")
            )
        
        elif tool_name == "get_patient_medications":
            result = await fhir_client.get_patient_medications(
                args["patientId"],
                args.get("status")
            )
        
        elif tool_name == "get_patient_observations":
            result = await fhir_client.get_patient_observations(
                GetPatientObservationsArgs(**args)
            )
        
        elif tool_name == "get_patient_encounters":
            result = await fhir_client.get_patient_encounters(
                GetPatientEncountersArgs(**args)
            )
        
        elif tool_name == "get_patient_allergies":
            result = await fhir_client.get_patient_allergies(args["patientId"])
        
        elif tool_name == "get_patient_everything":
            resource_types = args.get("resourceTypes", ["Observation", "Condition", "MedicationRequest"])
            result = await fhir_client.get_patient_everything(args["patientId"], resource_types)
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        logger.info(f"Tool {tool_name} executed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        raise Exception(f"Tool execution failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)