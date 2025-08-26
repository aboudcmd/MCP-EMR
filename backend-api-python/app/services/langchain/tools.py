"""
LangChain tools module for EMR system
"""
import json
import logging
import asyncio
from typing import List

from langchain.tools import Tool
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)


class EMRToolsFactory:
    """Factory for creating EMR-specific LangChain tools"""
    
    def __init__(self, mcp_client: HTTPMCPClient):
        self.mcp_client = mcp_client
    
    def create_tools(self) -> List[Tool]:
        """Create all EMR tools for LangChain agent"""
        tools = []
        
        # Search patients tool
        tools.append(Tool(
            name="search_patients",
            func=self._create_search_patients_wrapper(),
            description="Search for patients by name or ID. Use format: 'name:John Doe' or 'id:12345'"
        ))
        
        # Get patient details tool
        tools.append(Tool(
            name="get_patient_details",
            func=self._create_patient_details_wrapper(),
            description="Get comprehensive patient information. MUST USE for any patient info query."
        ))
        
        # Get patient conditions tool
        tools.append(Tool(
            name="get_patient_conditions",
            func=self._create_conditions_wrapper(),
            description="Get all medical conditions/diagnoses. MUST USE for diagnosis queries."
        ))
        
        # Get patient medications tool
        tools.append(Tool(
            name="get_patient_medications",
            func=self._create_medications_wrapper(),
            description="Get all medications/prescriptions. MUST USE for medication queries."
        ))
        
        # Get patient observations tool
        tools.append(Tool(
            name="get_patient_observations",
            func=self._create_observations_wrapper(),
            description="Get vital signs, lab results, observations. MUST USE for vitals/labs queries."
        ))
        
        # Get patient allergies tool
        tools.append(Tool(
            name="get_patient_allergies",
            func=self._create_allergies_wrapper(),
            description="Get allergy information. MUST USE for allergy queries."
        ))
        
        return tools
    
    def _create_search_patients_wrapper(self):
        """Create search patients wrapper function"""
        def search_patients_wrapper(query: str) -> str:
            """Search for patients - REQUIRED for finding patients"""
            try:
                # Parse query to extract search parameters
                params = {}
                if "name:" in query:
                    params["name"] = query.split("name:")[1].split(",")[0].strip()
                if "id:" in query:
                    params["mrn"] = query.split("id:")[1].split(",")[0].strip()
                    
                result = asyncio.run(self.mcp_client.execute_tool("search_patients", params))
                return json.dumps(result) if result else "No patients found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error searching patients: {str(e)}"
        
        return search_patients_wrapper
    
    def _create_patient_details_wrapper(self):
        """Create patient details wrapper function"""
        def get_patient_details_wrapper(patient_id: str) -> str:
            """Get patient demographics - REQUIRED for patient info queries"""
            try:
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_details", {"patientId": patient_id.strip()}))
                return json.dumps(result) if result else "No patient details found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving patient details: {str(e)}"
        
        return get_patient_details_wrapper
    
    def _create_conditions_wrapper(self):
        """Create conditions wrapper function"""
        def get_conditions_wrapper(patient_id: str) -> str:
            """Get patient conditions - REQUIRED for diagnosis queries"""
            try:
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_conditions", {"patientId": patient_id.strip()}))
                return json.dumps(result) if result else "No conditions found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving conditions: {str(e)}"
        
        return get_conditions_wrapper
    
    def _create_medications_wrapper(self):
        """Create medications wrapper function"""
        def get_medications_wrapper(patient_id: str) -> str:
            """Get patient medications - REQUIRED for medication queries"""
            try:
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_medications", {"patientId": patient_id.strip()}))
                return json.dumps(result) if result else "No medications found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving medications: {str(e)}"
        
        return get_medications_wrapper
    
    def _create_observations_wrapper(self):
        """Create observations wrapper function"""
        def get_observations_wrapper(patient_id: str) -> str:
            """Get patient observations - REQUIRED for vitals/lab queries"""
            try:
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_observations", {"patientId": patient_id.strip()}))
                return json.dumps(result) if result else "No observations found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving observations: {str(e)}"
        
        return get_observations_wrapper
    
    def _create_allergies_wrapper(self):
        """Create allergies wrapper function"""
        def get_allergies_wrapper(patient_id: str) -> str:
            """Get patient allergies - REQUIRED for allergy queries"""
            try:
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_allergies", {"patientId": patient_id.strip()}))
                return json.dumps(result) if result else "No allergies found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving allergies: {str(e)}"
        
        return get_allergies_wrapper