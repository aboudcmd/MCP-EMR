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
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(test_patient_search())