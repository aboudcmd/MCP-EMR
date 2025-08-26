"""
LangChain tools module for EMR system
"""
import json
import logging
import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor
import threading

from langchain.tools import Tool
from langchain.agents import tool
from langchain_core.tools import StructuredTool
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)


class EMRToolsFactory:
    """Factory for creating EMR-specific LangChain tools"""
    
    def __init__(self, mcp_client: HTTPMCPClient):
        self.mcp_client = mcp_client
    
    def _run_async_safely(self, coro):
        """Safely run async coroutine from sync context"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(coro)
        
        # There is a running loop, we need to run in a separate thread
        def run_in_thread():
            return asyncio.run(coro)
        
        with ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=60)  # 60 second timeout
    
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
                logger.info(f"🔧 Tool wrapper: search_patients called with {query}")
                # Parse query to extract search parameters
                params = {}
                if "name:" in query:
                    params["name"] = query.split("name:")[1].split(",")[0].strip()
                if "id:" in query:
                    params["mrn"] = query.split("id:")[1].split(",")[0].strip()
                    
                result = self._run_async_safely(self.mcp_client.execute_tool("search_patients", params))
                    
                logger.info(f"🔧 Tool wrapper: search_patients completed successfully")
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
                logger.info(f"🔧 Tool wrapper: get_patient_details called with {patient_id}")
                result = self._run_async_safely(self.mcp_client.execute_tool("get_patient_details", {"patientId": patient_id.strip()}))
                logger.info(f"🔧 Tool wrapper: get_patient_details completed successfully")
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
                logger.info(f"🔧 Tool wrapper: get_patient_conditions called with {patient_id}")
                result = self._run_async_safely(self.mcp_client.execute_tool("get_patient_conditions", {"patientId": patient_id.strip()}))
                logger.info(f"🔧 Tool wrapper: get_patient_conditions completed successfully")
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
                logger.info(f"🔧 Tool wrapper: get_patient_medications called with {patient_id}")
                result = self._run_async_safely(self.mcp_client.execute_tool("get_patient_medications", {"patientId": patient_id.strip()}))
                logger.info(f"🔧 Tool wrapper: get_patient_medications completed successfully")
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
                logger.info(f"🔧 Tool wrapper: get_patient_observations called with {patient_id}")
                result = self._run_async_safely(self.mcp_client.execute_tool("get_patient_observations", {"patientId": patient_id.strip()}))
                logger.info(f"🔧 Tool wrapper: get_patient_observations completed successfully")
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
                logger.info(f"🔧 Tool wrapper: get_patient_allergies called with {patient_id}")
                result = self._run_async_safely(self.mcp_client.execute_tool("get_patient_allergies", {"patientId": patient_id.strip()}))
                logger.info(f"🔧 Tool wrapper: get_patient_allergies completed successfully")
                return json.dumps(result) if result else "No allergies found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving allergies: {str(e)}"
        
        return get_allergies_wrapper