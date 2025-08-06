import os
import sys
import json
import asyncio
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

# Load environment variables
load_dotenv()

# Initialize FHIR client
fhir_client = FHIRClient(
    base_url=os.getenv("FHIR_SERVER_URL", "http://10.201.205.101:8007/")
)

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

async def main():
    """Main entry point for the MCP server"""
    # Read request from stdin
    request_data = sys.stdin.read()
    
    try:
        request = json.loads(request_data)
        
        # Execute the tool
        result = await execute_tool(
            request["params"]["name"],
            request["params"]["arguments"]
        )
        
        # Send response
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request["id"]
        }
        
        print(json.dumps(response))
        sys.exit(0)
        
    except Exception as e:
        # Send error response
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": 1
        }
        
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())