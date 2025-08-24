"""
Chat service for handling EMR conversations
"""
import json
import logging
from typing import List, Dict, Any, Tuple

from app.config import settings
from app.prompts import SYSTEM_PROMPT, get_patient_context_prompt, get_no_patient_prompt
from app.services.session_service import SessionService
from app.models import SessionData
from groq_client import GroqClient
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)

class ChatService:
    """Service for handling chat requests with EMR integration"""
    
    def __init__(self, groq_client: GroqClient, mcp_client: HTTPMCPClient, session_service: SessionService):
        self.groq_client = groq_client
        self.mcp_client = mcp_client
        self.session_service = session_service
        self.tools = self._get_tools()
    
    async def process_chat(self, message: str, patient_id: str = None) -> Tuple[str, str]:
        """
        Process a chat message and return response
        Returns: (response_content, patient_id)
        """
        logger.info(f"Processing chat: message='{message}', patient_id='{patient_id}'")
        
        # Get patient-scoped session
        current_patient_id, session = await self.session_service.get_patient_session(patient_id)
        
        # Build conversation messages
        messages = self._build_messages(current_patient_id, session, message)
        
        # Check if user needs patient ID
        if self._needs_patient_id(message, current_patient_id):
            response_content = "I need a patient ID to retrieve medical information. Please provide the patient ID or search for a patient first."
        else:
            # Get LLM response
            response_content = await self._get_llm_response(messages, current_patient_id)
        
        # Update session history
        if current_patient_id:
            await self.session_service.add_to_history(current_patient_id, message, response_content)
        
        return response_content, current_patient_id
    
    def _build_messages(self, patient_id: str, session: SessionData, current_message: str) -> List[Dict[str, Any]]:
        """Build conversation messages for LLM"""
        messages = []
        
        # Add system prompt with patient context
        system_content = SYSTEM_PROMPT
        if patient_id:
            system_content += get_patient_context_prompt(patient_id)
        else:
            system_content += get_no_patient_prompt()
        
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        history_messages = session.history[-settings.MAX_CONVERSATION_HISTORY:]
        for msg in history_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def _needs_patient_id(self, message: str, patient_id: str) -> bool:
        """Check if message needs patient ID but doesn't have one"""
        keywords = [
            'discharge', 'summary', 'patient', 'medication', 'condition', 
            'diagnosis', 'allergy', 'vital', 'observation'
        ]
        needs_patient_id = any(keyword in message.lower() for keyword in keywords)
        return needs_patient_id and not patient_id and "search" not in message.lower()
    
    async def _get_llm_response(self, messages: List[Dict[str, Any]], patient_id: str) -> str:
        """Get response from LLM with tool execution"""
        logger.info("Calling LLM with anti-hallucination prompt...")
        
        response = await self.groq_client.chat(messages, self.tools, SYSTEM_PROMPT)
        response_message = response.choices[0].message
        
        # Process tool calls if any
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            logger.info(f"LLM using {len(response_message.tool_calls)} tools")
            return await self._process_tool_calls(messages, response_message, patient_id)
        else:
            logger.info("LLM responded without using tools")
            return response_message.content
    
    async def _process_tool_calls(self, messages: List[Dict[str, Any]], response_message, patient_id: str) -> str:
        """Process LLM tool calls and get final response"""
        # Add assistant's tool call message
        messages.append({
            "role": "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in response_message.tool_calls
            ]
        })
        
        # Execute tools and collect results
        tool_results = []
        for tool_call in response_message.tool_calls:
            try:
                logger.info(f"Executing tool: {tool_call.function.name}")
                
                # Parse arguments
                args = json.loads(tool_call.function.arguments)
                
                # Auto-inject patient ID if available and not provided
                if patient_id and 'patientId' not in args and tool_call.function.name != 'search_patients':
                    args['patientId'] = patient_id
                
                # Execute tool
                result = await self.mcp_client.execute_tool(tool_call.function.name, args)
                logger.info(f"Tool {tool_call.function.name} completed")
                
                tool_results.append(result)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                    "tool_call_id": tool_call.id,
                })
                
            except Exception as e:
                logger.error(f"Tool error: {e}")
                error_result = {"error": str(e)}
                tool_results.append(error_result)
                messages.append({
                    "role": "tool",
                    "content": json.dumps(error_result),
                    "tool_call_id": tool_call.id,
                })
        
        # Check if all tools returned empty results
        all_empty = all(
            (isinstance(r, dict) and (r.get('total') == 0 or r.get('results') == [] or r == {}))
            for r in tool_results
        )
        
        if all_empty:
            logger.info("All tools returned empty results")
            return "No data was found in the EMR system for this query. The patient may not have records for the requested information, or the patient ID may not exist in the system."
        
        # Get final response from LLM with tool results
        logger.info("Getting final response from LLM with tool results...")
        final_response = await self.groq_client.chat(messages, [], SYSTEM_PROMPT)
        return final_response.choices[0].message.content
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_patients",
                    "description": "Search for patients by various criteria like name, ID, or demographics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Patient name"},
                            "mrn": {"type": "string", "description": "Medical Record Number"},
                            "nationalId": {"type": "string", "description": "National ID"},
                            "iqama": {"type": "string", "description": "Iqama number"},
                            "birthDate": {"type": "string", "description": "Birth date (YYYY-MM-DD)"},
                            "gender": {"type": "string", "enum": ["male", "female", "other"]},
                            "phone": {"type": "string", "description": "Phone number"},
                            "email": {"type": "string", "description": "Email address"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patient_details",
                    "description": "Get comprehensive information about a specific patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patientId": {"type": "string", "description": "Patient ID"},
                        },
                        "required": ["patientId"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patient_conditions",
                    "description": "Retrieve all medical conditions and diagnoses for a patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patientId": {"type": "string", "description": "Patient ID"},
                            "clinicalStatus": {
                                "type": "string",
                                "enum": ["active", "recurrence", "relapse", "inactive", "remission", "resolved"],
                                "description": "Filter by clinical status"
                            },
                        },
                        "required": ["patientId"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patient_medications",
                    "description": "Get all medications and prescriptions for a patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patientId": {"type": "string", "description": "Patient ID"},
                            "status": {
                                "type": "string",
                                "enum": ["active", "completed", "stopped", "on-hold", "cancelled"],
                                "description": "Filter by medication status"
                            },
                        },
                        "required": ["patientId"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patient_observations",
                    "description": "Retrieve vital signs, lab results, and other observations for a patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patientId": {"type": "string", "description": "Patient ID"},
                            "category": {"type": "string", "description": "Category of observation"},
                            "code": {"type": "string", "description": "LOINC code"},
                            "dateFrom": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "dateTo": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        },
                        "required": ["patientId"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patient_allergies",
                    "description": "Get allergy and intolerance information for a patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patientId": {"type": "string", "description": "Patient ID"},
                        },
                        "required": ["patientId"],
                    },
                },
            },
        ]