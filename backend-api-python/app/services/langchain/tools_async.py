"""
Async-compatible LangChain tools for EMR system
"""
import json
import logging
import asyncio
from typing import Optional, Type, List
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun

from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)

# Global semaphore to ensure sequential tool execution
TOOL_EXECUTION_LOCK = asyncio.Semaphore(1)


class PatientIdInput(BaseModel):
    """Input for patient-specific tools"""
    patient_id: str = Field(description="The patient ID")


class SearchPatientInput(BaseModel):
    """Input for patient search"""
    query: str = Field(description="Search query (e.g., 'name:John Doe' or 'id:12345')")


class AsyncEMRTool(BaseTool):
    """Base class for async EMR tools"""
    mcp_client: HTTPMCPClient
    
    class Config:
        arbitrary_types_allowed = True
    
    async def _arun(
        self,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Async implementation - must be overridden"""
        raise NotImplementedError("Async implementation required")
    
    def _run(self, *args, **kwargs) -> str:
        """Sync implementation - not used"""
        raise NotImplementedError("Use async version")


class GetPatientDetailsTool(AsyncEMRTool):
    """Tool to get patient details"""
    name: str = "get_patient_details"
    description: str = "Get comprehensive patient information. MUST USE for any patient info query."
    args_schema: Type[BaseModel] = PatientIdInput
    
    async def _arun(
        self,
        patient_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Get patient details asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: get_patient_details called with {patient_id}")
                result = await self.mcp_client.execute_tool(
                    "get_patient_details", 
                    {"patientId": patient_id.strip()}
                )
                logger.info(f"🔧 Async tool: get_patient_details completed")
                return json.dumps(result) if result else "No patient details found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error retrieving patient details: {str(e)}"


class GetPatientConditionsTool(AsyncEMRTool):
    """Tool to get patient conditions"""
    name: str = "get_patient_conditions"
    description: str = "Get all medical conditions/diagnoses. MUST USE for diagnosis queries."
    args_schema: Type[BaseModel] = PatientIdInput
    
    async def _arun(
        self,
        patient_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Get patient conditions asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: get_patient_conditions called with {patient_id}")
                result = await self.mcp_client.execute_tool(
                    "get_patient_conditions",
                    {"patientId": patient_id.strip()}
                )
                logger.info(f"🔧 Async tool: get_patient_conditions completed")
                return json.dumps(result) if result else "No conditions found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error retrieving conditions: {str(e)}"


class GetPatientMedicationsTool(AsyncEMRTool):
    """Tool to get patient medications"""
    name: str = "get_patient_medications"
    description: str = "Get all medications/prescriptions. MUST USE for medication queries."
    args_schema: Type[BaseModel] = PatientIdInput
    
    async def _arun(
        self,
        patient_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Get patient medications asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: get_patient_medications called with {patient_id}")
                result = await self.mcp_client.execute_tool(
                    "get_patient_medications",
                    {"patientId": patient_id.strip()}
                )
                logger.info(f"🔧 Async tool: get_patient_medications completed")
                return json.dumps(result) if result else "No medications found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error retrieving medications: {str(e)}"


class GetPatientObservationsTool(AsyncEMRTool):
    """Tool to get patient observations including vitals, labs, and imaging"""
    name: str = "get_patient_observations"
    description: str = """Get patient observations including:
    - Vital signs (blood pressure, weight, temperature, heart rate, etc.)
    - Laboratory results (blood tests, cholesterol, glucose, CBC, etc.)
    - Radiology/Imaging reports (X-ray, CT, MRI findings and interpretations)
    MUST USE for any queries about vitals, labs, test results, imaging, radiology, or diagnostic findings."""
    args_schema: Type[BaseModel] = PatientIdInput
    
    async def _arun(
        self,
        patient_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Get patient observations asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: get_patient_observations called with {patient_id}")
                result = await self.mcp_client.execute_tool(
                    "get_patient_observations",
                    {"patientId": patient_id.strip()}
                )
                logger.info(f"🔧 Async tool: get_patient_observations completed")
                return json.dumps(result) if result else "No observations found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error retrieving observations: {str(e)}"


class GetPatientAllergiesTool(AsyncEMRTool):
    """Tool to get patient allergies"""
    name: str = "get_patient_allergies"
    description: str = "Get allergy information. MUST USE for allergy queries."
    args_schema: Type[BaseModel] = PatientIdInput
    
    async def _arun(
        self,
        patient_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Get patient allergies asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: get_patient_allergies called with {patient_id}")
                result = await self.mcp_client.execute_tool(
                    "get_patient_allergies",
                    {"patientId": patient_id.strip()}
                )
                logger.info(f"🔧 Async tool: get_patient_allergies completed")
                return json.dumps(result) if result else "No allergies found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error retrieving allergies: {str(e)}"


class SearchPatientsTool(AsyncEMRTool):
    """Tool to search for patients"""
    name: str = "search_patients"
    description: str = "Search for patients by name or ID. Use format: 'name:John Doe' or 'id:12345'"
    args_schema: Type[BaseModel] = SearchPatientInput

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Search patients asynchronously"""
        async with TOOL_EXECUTION_LOCK:
            try:
                logger.info(f"🔧 Async tool: search_patients called with {query}")
                # Parse query to extract search parameters
                params = {}
                if "name:" in query:
                    params["name"] = query.split("name:")[1].split(",")[0].strip()
                if "id:" in query:
                    params["mrn"] = query.split("id:")[1].split(",")[0].strip()

                result = await self.mcp_client.execute_tool("search_patients", params)
                logger.info(f"🔧 Async tool: search_patients completed")
                return json.dumps(result) if result else "No patients found"
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return f"Error searching patients: {str(e)}"


def create_async_emr_tools(mcp_client: HTTPMCPClient) -> List[BaseTool]:
    """Create all async EMR tools"""
    return [
        SearchPatientsTool(mcp_client=mcp_client),
        GetPatientDetailsTool(mcp_client=mcp_client),
        GetPatientConditionsTool(mcp_client=mcp_client),
        GetPatientMedicationsTool(mcp_client=mcp_client),
        GetPatientObservationsTool(mcp_client=mcp_client),
        GetPatientAllergiesTool(mcp_client=mcp_client),
    ]