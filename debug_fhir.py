#!/usr/bin/env python3
"""Debug FHIR observation queries"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add mcp-server-python to path
sys.path.append(str(Path(__file__).parent / "mcp-server-python"))

from fhir_client import FHIRClient
from types_models import GetPatientObservationsArgs

# Load environment variables
load_dotenv()

async def test_observations():
    """Test observation queries"""
    
    # Initialize FHIR client
    fhir_client = FHIRClient(
        base_url=os.getenv("FHIR_SERVER_URL", "http://10.201.205.101:8007/")
    )
    
    print(f"FHIR Server URL: {fhir_client.base_url}")
    
    # Test patient 416768 observations
    patient_id = "416768"
    print(f"\n=== Testing observations for patient {patient_id} ===")
    
    try:
        args = GetPatientObservationsArgs(patientId=patient_id)
        result = await fhir_client.get_patient_observations(args)
        
        print(f"Result: {result}")
        print(f"Total observations: {result.get('total', 0)}")
        print(f"Observations returned: {len(result.get('observations', []))}")
        
        if result.get('observations'):
            for i, obs in enumerate(result['observations'][:3]):  # Show first 3
                print(f"  {i+1}. {obs.get('type', 'Unknown')}: {obs.get('value', 'No value')}")
    
    except Exception as e:
        print(f"Error querying observations: {e}")
        import traceback
        traceback.print_exc()
    
    # Test patient details to make sure patient exists
    print(f"\n=== Testing patient details for {patient_id} ===")
    try:
        patient_details = await fhir_client.get_patient_details(patient_id)
        print(f"Patient found: {patient_details.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error getting patient details: {e}")

if __name__ == "__main__":
    asyncio.run(test_observations())