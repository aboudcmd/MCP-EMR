#!/usr/bin/env python3
"""
Quick test script for Spark FHIR server integration
"""
import asyncio
import json
import sys
import os

# Add the mcp-server-python directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-server-python'))

from fhir_client import FHIRClient
from types_models import SearchPatientsArgs

async def test_patient_search():
    """Test patient search functionality"""
    print("Testing Spark FHIR server integration...")
    
    # Initialize client
    client = FHIRClient("http://10.201.205.101:8007/")
    
    # Test 1: Search all patients
    print("\n1. Testing search all patients:")
    try:
        args = SearchPatientsArgs()
        result = await client.search_patients(args)
        print(f"   Found {result.get('total', 0)} patients")
        if result.get('results'):
            print(f"   First patient: {result['results'][0]['name']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Search by name
    print("\n2. Testing search by name (SARAH):")
    try:
        args = SearchPatientsArgs(name="SARAH")
        result = await client.search_patients(args)
        print(f"   Found {result.get('total', 0)} patients")
        if result.get('results'):
            patient = result['results'][0]
            print(f"   Patient: {patient['name']}")
            print(f"   MRN: {patient['mrn']}")
            print(f"   National ID: {patient['nationalId']}")
            print(f"   Gender: {patient['gender']}")
            print(f"   Phone: {patient['phone']}")
            print(f"   Email: {patient['email']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Search by MRN
    print("\n3. Testing search by MRN (10868):")
    try:
        args = SearchPatientsArgs(mrn="10868")
        result = await client.search_patients(args)
        print(f"   Found {result.get('total', 0)} patients")
        if result.get('results'):
            patient = result['results'][0]
            print(f"   Patient: {patient['name']}")
            print(f"   MRN: {patient['mrn']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Get patient details
    print("\n4. Testing get patient details (ID: 10868):")
    try:
        result = await client.get_patient_details("10868")
        print(f"   Patient: {result['name']}")
        print(f"   Birth Date: {result['birthDate']}")
        print(f"   Marital Status: {result['maritalStatus']}")
        print(f"   Citizenship: {result['citizenship']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Get patient conditions (try different patient IDs)
    for patient_id in ["10868", "2540335", "12345"]:
        print(f"\n5.{patient_id}: Testing get patient conditions (ID: {patient_id}):")
        try:
            result = await client.get_patient_conditions(patient_id)
            if result:
                print(f"   Found conditions: {json.dumps(result, indent=2)}")
            else:
                print("   No conditions found")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 6: Get patient observations (try different patient IDs)
    for patient_id in ["10868", "2540335", "12345"]:
        print(f"\n6.{patient_id}: Testing get patient observations (ID: {patient_id}):")
        try:
            from types_models import GetPatientObservationsArgs
            args = GetPatientObservationsArgs(patientId=patient_id)
            result = await client.get_patient_observations(args)
            if result:
                print(f"   Found observations: {json.dumps(result, indent=2)}")
            else:
                print("   No observations found")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 7: Get sample MedicationRequest data
    print(f"\n7. Testing MedicationRequest data structure:")
    try:
        # Get all MedicationRequests to see structure
        raw_data = await client._make_request("GET", "/MedicationRequest", {"_count": "3"})
        print(f"   MedicationRequest count: {raw_data.get('total', 0)}")
        if raw_data.get("entry"):
            print(f"   Sample MedicationRequest: {json.dumps(raw_data['entry'][0]['resource'], indent=2)}")
        else:
            print("   No MedicationRequest entries found")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 8: Get raw MedicationRequest data for patient 2540335
    print(f"\n8. Testing raw MedicationRequest data for patient 2540335:")
    try:
        raw_data = await client._make_request("GET", "/MedicationRequest", {"patient": "2540335"})
        print(f"   Raw FHIR bundle: {json.dumps(raw_data, indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 9: Test existing medications tool with known patients including 937066
    for patient_id in ["937066", "2540335", "10868", "12345"]:
        print(f"\n9.{patient_id}: Testing get patient medications (ID: {patient_id}):")
        try:
            result = await client.get_patient_medications(patient_id)
            if result:
                print(f"   Found medications: {json.dumps(result, indent=2)}")
            else:
                print("   No medications found")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 10: Debug raw MedicationRequest data for patient 937066
    print(f"\n10. Testing raw MedicationRequest data for patient 937066:")
    try:
        raw_data = await client._make_request("GET", "/MedicationRequest", {"patient": "937066", "_count": "2"})
        print(f"   Total found: {raw_data.get('total', 0)}")
        if raw_data.get("entry"):
            print(f"   Sample entry: {json.dumps(raw_data['entry'][0]['resource'], indent=2)}")
        else:
            print("   No entries in response")
            print(f"   Raw response: {json.dumps(raw_data, indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(test_patient_search())