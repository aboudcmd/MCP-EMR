# backend-api-python/main.py
import os
import json  
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from groq_client import GroqClient
from http_mcp_client import HTTPMCPClient

# Load environment variables
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="EMR Backend API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
groq_client = GroqClient(os.getenv("GROQ_API_KEY", ""))
mcp_client = HTTPMCPClient(
    mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8001")
)

# Global variables for conversation management  
max_context_length = 15  # Keep last 15 messages to prevent context exhaustion
current_patient_context = {}  # Track current patient ID per session

# Request/Response models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    patientId: str = Field(
        description="The patient ID/MRN to query. All queries will be for this specific patient."
    )
    conversationHistory: List[Message] = Field(
        default=[],
        description="Full conversation history for context. Send all previous messages to maintain conversation state."
    )

class ChatResponse(BaseModel):
    response: str
    conversationHistory: List[Message]

# Define tools for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_patients",
            "description": "Search for patients in Saudi healthcare system. Supports name, MRN, National ID, Iqama, and other criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Patient name to search for"},
                    "mrn": {"type": "string", "description": "Medical Record Number (MRN)"},
                    "nationalId": {"type": "string", "description": "Saudi National ID number"},
                    "iqama": {"type": "string", "description": "Iqama number for residents"},
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
            "description": "Get detailed information about a specific patient",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                },
                "required": ["patientId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_conditions",
            "description": "Get all conditions/diagnoses for a patient",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                    "clinicalStatus": {
                        "type": "string",
                        "enum": ["active", "recurrence", "relapse", "inactive", "remission", "resolved"],
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
            "description": "Get current medications for a patient",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                    "status": {"type": "string", "enum": ["active", "completed", "stopped"]},
                },
                "required": ["patientId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_observations",
            "description": "Get observations (vitals, lab results) for a patient",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                    "category": {"type": "string", "description": "Category of observation"},
                    "code": {"type": "string", "description": "LOINC code for specific observation"},
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
            "name": "get_patient_encounters",
            "description": "Get encounters/visits for a patient",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                    "type": {"type": "string", "description": "Type of encounter"},
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
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                },
                "required": ["patientId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_everything",
            "description": "Get comprehensive patient data including conditions, medications, observations, allergies, and encounters using the $everything endpoint",
            "parameters": {
                "type": "object",
                "properties": {
                    "patientId": {"type": "string", "description": "FHIR Patient resource ID"},
                    "resourceTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific resource types to include (default: Observation, Condition, MedicationRequest)",
                        "default": ["Observation", "Condition", "MedicationRequest"]
                    }
                },
                "required": ["patientId"],
            },
        },
    },
]

# SYSTEM_PROMPT = """You are an EMR assistant. 

# MANDATORY RULE: When asked about patient medications, you MUST ALWAYS call get_patient_medications tool.
# When asked about conditions/diagnoses, you MUST ALWAYS call get_patient_conditions tool.
# When asked about observations/vitals, you MUST ALWAYS call get_patient_observations tool.

# You cannot answer medical questions without calling the appropriate tool first.
# """

SYSTEM_PROMPT = """You are an EMR (Electronic Medical Records) assistant. You MUST follow these rules WITHOUT EXCEPTION:

🚨 MANDATORY RULES:
1. TOOL USAGE: For ANY medical query, you MUST call a tool. DO NOT answer from memory.
2. TOOL RESULTS: When you receive "TOOL RESULT:" in a message, that is the ONLY data you can use. 
   - If it says "No data found" or "No medications/conditions/observations found", you MUST tell the user exactly that.
   - NEVER make up data when tools return empty results.
   - ALWAYS use the exact information from TOOL RESULT messages.

3. FOLLOW-UP QUERIES: When users ask "what about their medications/conditions" - call the appropriate tool.

4. NO HALLUCINATION RULE:
   - If tool returns empty/no data → Say "No [type] found for this patient"
   - If tool returns data → Use ONLY that exact data
   - NEVER invent medical information
   - NEVER say "Based on previous information" - use tool results

5. Tool mapping:
   - medications/drugs/prescriptions → get_patient_medications
   - conditions/diagnoses/problems → get_patient_conditions
   - observations/vitals/labs → get_patient_observations
   - information/details → get_patient_details
   - allergies → get_patient_allergies
   - visits/encounters → get_patient_encounters

VIOLATING THESE RULES IS A CRITICAL SYSTEM FAILURE."""

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "backend": "running",
            "port": int(os.getenv("PORT", 3001))
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests"""
    try:
        logger.info(f"Received chat request: {request.message}")
        
        # Use the patient ID provided by the frontend
        patient_id = request.patientId
        if not patient_id:
            raise HTTPException(status_code=400, detail="Patient ID is required")
        
        # Validate patient ID format
        if not _validate_patient_id(patient_id):
            raise HTTPException(status_code=400, detail="Invalid patient ID format. Must be 4-7 digits.")
        
        logger.info(f"Processing request for patient: {patient_id}")
        
        # Truncate conversation history to prevent context exhaustion
        conversation_history = request.conversationHistory
        if len(conversation_history) > max_context_length:
            conversation_history = conversation_history[-max_context_length:]
            logger.info(f"Truncated conversation history to last {max_context_length} messages")
        
        # Build conversation history
        messages = []
        
        # Add system prompt with the specific patient context
        system_content = SYSTEM_PROMPT + f"\n\nIMPORTANT: You are ONLY allowed to query data for Patient ID {patient_id}. All tool calls MUST use patientId: '{patient_id}'. Do not accept or process queries about other patients."
        messages.append({"role": "system", "content": system_content})
        
        # Add truncated conversation history
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message with context injection for follow-ups
        user_message = request.message
        
        # Always inject the patient ID into queries about medical data
        if _needs_patient_context(user_message):
            # Make the query explicit with the patient ID
            if 'condition' in user_message.lower():
                user_message = f"Get conditions for patient {patient_id}"
            elif 'medication' in user_message.lower() or 'drug' in user_message.lower():
                user_message = f"Get medications for patient {patient_id}"
            elif 'observation' in user_message.lower() or 'vital' in user_message.lower():
                user_message = f"Get observations/vitals for patient {patient_id}"
            elif 'allerg' in user_message.lower():
                user_message = f"Get allergies for patient {patient_id}"
            elif 'information' in user_message.lower() or 'detail' in user_message.lower():
                user_message = f"Get patient details for patient {patient_id}"
            else:
                # Add patient context to any medical query
                user_message = f"{user_message} for patient {patient_id}"
            
            logger.info(f"Added patient context to query: {user_message}")
        
        messages.append({"role": "user", "content": user_message})
        
        # Get initial response from Groq with tools
        initial_response = await groq_client.chat(messages, TOOLS, SYSTEM_PROMPT)
        response_message = initial_response.choices[0].message
        
        # Check if Groq wants to use tools
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            logger.info(f"Executing {len(response_message.tool_calls)} tool calls")
            # Log which tools the LLM decided to call
            tool_names = [tc.function.name for tc in response_message.tool_calls]
            logger.info(f"LLM decided to call tools: {tool_names}")
            
            # Add the assistant's message with tool calls to the conversation
            assistant_msg = {
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": []
            }
            
            # Format tool calls properly
            for tc in response_message.tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
            
            messages.append(assistant_msg)
            
            # Execute each tool call and collect results
            for tool_call in response_message.tool_calls:
                try:
                    logger.info(f"Executing tool: {tool_call.function.name}")
                    
                    # Execute the tool via HTTP MCP service
                    result = await mcp_client.execute_tool(
                        tool_call.function.name,
                        tool_call.function.arguments
                    )
                    
                    logger.info(f"Tool {tool_call.function.name} executed successfully")
                    
                    # Add tool result to messages with summarized content
                    # Format the result for better context management
                    formatted_result = _format_tool_result(result, tool_call.function.name)
                    
                    # Log the formatted result for debugging (show more for debugging)
                    logger.info(f"Formatted tool result length: {len(formatted_result)} chars")
                    if len(formatted_result) > 500:
                        logger.info(f"Tool result preview: {formatted_result[:500]}...")
                    else:
                        logger.info(f"Tool result: {formatted_result}")
                    
                    tool_result_msg = {
                        "role": "tool",
                        "content": formatted_result,
                        "tool_call_id": tool_call.id,
                    }
                    messages.append(tool_result_msg)
                   
                except Exception as e:
                    logger.error(f"Tool execution error for {tool_call.function.name}: {e}")
                    # Add error as tool result
                    error_msg = {
                        "role": "tool",
                        "content": json.dumps({"error": str(e)}),
                        "tool_call_id": tool_call.id,
                    }
                    messages.append(error_msg)
           
           # Get final response from Groq with tool results
           # Add explicit instruction to use tool results
            messages.append({
                "role": "system",
                "content": "CRITICAL: You MUST use ONLY the data from the tool results above. Do NOT make up any information. If the tool returned 'No data found' or empty results, say exactly that. The tool results are the ONLY source of truth."
            })
            
            # Important: Don't pass tools this time to force response generation
            final_response = await groq_client.chat(messages, [], SYSTEM_PROMPT)
            final_message = final_response.choices[0].message
           
           # Return the response
            # Handle None content from LLM response
            response_content = final_message.content or "I successfully retrieved the requested information."
            
            # Store a summary of tool results in context instead of raw data
            tool_summary = _create_tool_summary(response_message.tool_calls, messages)
            
            # Update conversation history with truncation and tool summary
            updated_history = conversation_history + [
                Message(role="user", content=request.message),
                Message(role="assistant", content=f"{response_content}\n[Context: {tool_summary}]")
            ]
            
            return ChatResponse(
                response=response_content,
                conversationHistory=updated_history
            )
        else:
            # LLM didn't use tools - check if it should have
            logger.warning("LLM did not call any tools despite having access to them")
            
            # Check if this query actually needs tools
            query_needs_tools = _query_requires_tools(request.message, patient_id)
            
            if query_needs_tools:
                # Retry with more explicit instruction
                logger.info("Retrying with explicit tool instruction")
                
                # Add an explicit system message
                retry_messages = messages.copy()
                retry_messages.append({
                    "role": "system",
                    "content": "YOU MUST USE A TOOL TO ANSWER THIS QUERY. The user is asking about medical data. Select and call the appropriate tool NOW."
                })
                
                # Make the user message more explicit
                explicit_message = _make_query_explicit(request.message, patient_id)
                retry_messages[-1] = {"role": "user", "content": explicit_message}
                
                # Retry with explicit instructions
                retry_response = await groq_client.chat(retry_messages, TOOLS, SYSTEM_PROMPT)
                retry_message = retry_response.choices[0].message
                
                if hasattr(retry_message, 'tool_calls') and retry_message.tool_calls:
                    # Success! Process the tool calls
                    logger.info("Retry successful - LLM used tools")
                    
                    # Process tool calls (same logic as above)
                    assistant_msg = {
                        "role": "assistant",
                        "content": retry_message.content or "",
                        "tool_calls": []
                    }
                    
                    for tc in retry_message.tool_calls:
                        assistant_msg["tool_calls"].append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                    
                    retry_messages.append(assistant_msg)
                    
                    # Execute tool calls
                    for tool_call in retry_message.tool_calls:
                        try:
                            result = await mcp_client.execute_tool(
                                tool_call.function.name,
                                tool_call.function.arguments
                            )
                            
                            formatted_result = _format_tool_result(result, tool_call.function.name)
                            
                            # Log the formatted result for debugging
                            logger.info(f"Retry formatted result preview: {formatted_result[:200]}...")
                            
                            tool_result_msg = {
                                "role": "tool",
                                "content": formatted_result,
                                "tool_call_id": tool_call.id,
                            }
                            retry_messages.append(tool_result_msg)
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            error_msg = {
                                "role": "tool",
                                "content": json.dumps({"error": str(e)}),
                                "tool_call_id": tool_call.id,
                            }
                            retry_messages.append(error_msg)
                    
                    # Add explicit instruction for retry
                    retry_messages.append({
                        "role": "system",
                        "content": "CRITICAL: Use ONLY the TOOL RESULT data above. If it says 'No data found', tell the user that. Do NOT make up information."
                    })
                    
                    # Get final response
                    final_response = await groq_client.chat(retry_messages, [], SYSTEM_PROMPT)
                    final_message = final_response.choices[0].message
                    
                    response_content = final_message.content or "I successfully retrieved the requested information."
                    tool_summary = _create_tool_summary(retry_message.tool_calls, retry_messages)
                    
                    updated_history = conversation_history + [
                        Message(role="user", content=request.message),
                        Message(role="assistant", content=f"{response_content}\n[Context: {tool_summary}]")
                    ]
                    
                    return ChatResponse(
                        response=response_content,
                        conversationHistory=updated_history
                    )
                else:
                    logger.error("Retry failed - LLM still didn't use tools")
            
            # Return the original response if no retry needed or retry failed
            updated_history = conversation_history + [
                Message(role="user", content=request.message),
                Message(role="assistant", content=response_message.content)
            ]
            
            return ChatResponse(
                response=response_message.content,
                conversationHistory=updated_history
            )
           
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")

def _format_tool_result(result: Any, tool_name: str) -> str:
    """Format tool results to be more concise and context-friendly"""
    try:
        if isinstance(result, list):
            # For list results, summarize the count and key info
            count = len(result)
            if count == 0:
                return f"TOOL RESULT: No {tool_name.replace('get_patient_', '').replace('_', ' ')} found for this patient. Tell the user there is no data."
            
            # Create a summary based on tool type
            if "condition" in tool_name.lower():
                # Extract condition codes/names properly
                conditions = []
                for item in result[:5]:
                    if isinstance(item, dict):
                        code = item.get('code', 'Unknown condition')
                        if code and code != 'Unknown condition':
                            conditions.append(code)
                
                if conditions:
                    summary = f"TOOL RESULT: Found {count} conditions for this patient:\n"
                    for i, cond in enumerate(conditions, 1):
                        summary += f"{i}. {cond}\n"
                    if count > 5:
                        summary += f"... and {count - 5} more conditions"
                else:
                    summary = f"TOOL RESULT: Found {count} conditions (details available)"
                return summary
                
            elif "medication" in tool_name.lower():
                # Handle the medication structure from the API
                medications = []
                for item in result[:5]:
                    if isinstance(item, dict):
                        # Try different fields where medication name might be
                        med_name = (
                            item.get('medicationText') or 
                            item.get('medication', {}).get('text') or
                            item.get('medicationCodeableConcept', {}).get('text') or
                            'Unknown medication'
                        )
                        if med_name != 'Unknown medication':
                            medications.append(med_name)
                
                if medications:
                    summary = f"TOOL RESULT: Found {count} medications for this patient:\n"
                    for i, med in enumerate(medications, 1):
                        summary += f"{i}. {med}\n"
                    if count > 5:
                        summary += f"... and {count - 5} more medications"
                else:
                    summary = f"TOOL RESULT: Found {count} medications (details available)"
                return summary
                
            elif "observation" in tool_name.lower():
                # Format observations with full details
                # This is ALWAYS a dict with 'observations' key from our API
                return _format_observations_detailed(result)
                
            else:
                return f"Found {count} records"
        
        elif isinstance(result, dict):
            # Check if this is an observations result that wasn't caught above
            if 'observations' in result and 'total' in result:
                return _format_observations_detailed(result)
            
            # For dict results, extract key information
            if "error" in result:
                return f"TOOL ERROR: {result['error']} - Tell the user there was an error retrieving data."
            
            # For patient details, extract key demographics
            if "name" in result or "birthDate" in result:
                name = result.get('name', 'Unknown')
                birth = result.get('birthDate', 'Unknown')
                gender = result.get('gender', 'Unknown')
                mrn = result.get('mrn', '')
                if mrn:
                    return f"TOOL RESULT: Patient Details:\nName: {name}\nMRN: {mrn}\nBirth Date: {birth}\nGender: {gender}"
                else:
                    return f"TOOL RESULT: Patient Details:\nName: {name}\nBirth Date: {birth}\nGender: {gender}"
            
            # For paginated results with 'total' field
            if 'total' in result:
                total = result.get('total', 0)
                if total == 0:
                    resource_type = 'medications' if 'medications' in result else 'observations' if 'observations' in result else 'results'
                    return f"TOOL RESULT: No {resource_type} found for this patient. Tell the user there is no data."
                elif 'medications' in result:
                    meds = result.get('medications', [])
                    if meds:
                        summary = f"TOOL RESULT: Found {total} medications:\n"
                        for i, med in enumerate(meds[:5], 1):
                            med_name = med.get('medication', 'Unknown')
                            summary += f"{i}. {med_name}\n"
                        if len(meds) > 5:
                            summary += f"... and {len(meds) - 5} more"
                        return summary
                    return f"TOOL RESULT: {total} medications exist but details not available"
                # Observations should be handled above, but as fallback:
                elif 'observations' in result:
                    return _format_observations_detailed(result)
                elif 'results' in result:
                    return f"TOOL RESULT: Found {total} results"
            
            # Default: return a brief summary
            return "TOOL RESULT: Data retrieved successfully. Use this information in your response."
        
        else:
            result_str = str(result)[:200]  # Truncate if too long
            return f"TOOL RESULT: {result_str}"
            
    except Exception as e:
        logger.error(f"Error formatting tool result: {e}")
        return f"TOOL ERROR: Failed to format result - {str(e)[:100]}"

def _format_observations_detailed(result: Any) -> str:
    """Format observation results with full details"""
    if not isinstance(result, dict):
        return "TOOL RESULT: Invalid observation data format"
    
    obs_list = result.get('observations', [])
    total = result.get('total', len(obs_list))
    
    if total == 0:
        return "TOOL RESULT: No observations/vitals found for this patient. Tell the user there are no observations recorded."
    elif len(obs_list) == 0 and total > 0:
        return f"TOOL RESULT: {total} observations exist but data retrieval failed. Please retry."
    
    # Show observations with full details
    summary = f"TOOL RESULT: Found {total} vital sign observations for this patient. Here are the details:\n\n"
    
    # Show up to 10 observations with full details
    for i, obs in enumerate(obs_list[:10], 1):
        obs_type = obs.get('type') or obs.get('code', 'Unknown')
        value = obs.get('value', '')
        date = obs.get('effectiveDateTime', obs.get('effectiveDate', 'Date unknown'))
        
        # Format the date if it exists
        if date and date != 'Date unknown':
            try:
                # Parse ISO date and make it readable
                from datetime import datetime
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                date_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                date_str = date
        else:
            date_str = date
        
        summary += f"{i}. {obs_type}\n"
        summary += f"   Date: {date_str}\n"
        if value:
            summary += f"   Values: {value}\n"
        
        # Add components if they exist (for blood pressure, etc.)
        components = obs.get('components', [])
        if components and not value:
            for comp in components:
                comp_name = comp.get('code', 'Unknown')
                comp_val = comp.get('value', 'N/A')
                summary += f"   - {comp_name}: {comp_val}\n"
        
        summary += "\n"
    
    if len(obs_list) > 10:
        summary += f"... and {len(obs_list) - 10} more observations available\n"
    
    summary += "\nUse this data to answer the user's questions about vital signs."
    return summary

def _create_tool_summary(tool_calls: List[Any], messages: List[Dict]) -> str:
    """Create a summary of tool calls for context"""
    try:
        if not tool_calls:
            return "No tools used"
        
        summaries = []
        patient_ids = set()
        for tc in tool_calls:
            # Parse the arguments to get patient ID if available
            try:
                args = json.loads(tc.function.arguments)
                patient_id = args.get('patientId', '')
                if patient_id:
                    patient_ids.add(patient_id)
                    summaries.append(f"{tc.function.name} for patient {patient_id}")
                else:
                    summaries.append(tc.function.name)
            except:
                summaries.append(tc.function.name)
        
        context = "Tools used: " + ", ".join(summaries)
        if patient_ids:
            context += f" | Active patient: {', '.join(patient_ids)}"
        return context
        
    except Exception as e:
        logger.error(f"Error creating tool summary: {e}")
        return "Tools were used"

def _needs_patient_context(message: str) -> bool:
    """Check if a message is about medical data and needs patient context"""
    message_lower = message.lower()
    
    # Medical terms that require patient context
    medical_terms = [
        'condition', 'diagnosis', 'diagnose', 'problem',
        'medication', 'drug', 'prescription', 'medicine',
        'observation', 'vital', 'lab', 'test', 'result',
        'allergy', 'allergic', 'intolerance',
        'visit', 'encounter', 'appointment',
        'information', 'detail', 'data', 'record',
        'their', 'his', 'her', 'the patient'
    ]
    
    return any(term in message_lower for term in medical_terms)

def _query_requires_tools(message: str, patient_id: str = None) -> bool:
    """Determine if a query requires tool usage"""
    message_lower = message.lower()
    
    # Medical keywords that require tools
    medical_keywords = [
        'medication', 'drug', 'prescription', 'medicine',
        'condition', 'diagnosis', 'diagnose', 'problem',
        'observation', 'vital', 'lab', 'test', 'result',
        'allergy', 'allergic', 'intolerance',
        'visit', 'encounter', 'appointment',
        'information', 'detail', 'data', 'record'
    ]
    
    # Check for medical keywords
    for keyword in medical_keywords:
        if keyword in message_lower:
            return True
    
    # Check for follow-up patterns with patient context
    if patient_id:
        follow_up_words = ['their', 'his', 'her', 'the patient', 'what about', 'and']
        for word in follow_up_words:
            if word in message_lower:
                return True
    
    return False

def _make_query_explicit(message: str, patient_id: str = None) -> str:
    """Make a query more explicit for the LLM"""
    message_lower = message.lower()
    
    if not patient_id:
        return message
    
    # Map keywords to specific tool instructions
    if any(word in message_lower for word in ['medication', 'drug', 'prescription', 'med']):
        return f"CALL get_patient_medications tool for patient {patient_id} NOW"
    elif any(word in message_lower for word in ['condition', 'diagnosis', 'problem']):
        return f"CALL get_patient_conditions tool for patient {patient_id} NOW"
    elif any(word in message_lower for word in ['observation', 'vital', 'lab', 'test']):
        return f"CALL get_patient_observations tool for patient {patient_id} NOW"
    elif any(word in message_lower for word in ['allergy', 'allergic']):
        return f"CALL get_patient_allergies tool for patient {patient_id} NOW"
    elif any(word in message_lower for word in ['visit', 'encounter', 'appointment']):
        return f"CALL get_patient_encounters tool for patient {patient_id} NOW"
    elif any(word in message_lower for word in ['information', 'detail', 'data']):
        return f"CALL get_patient_details tool for patient {patient_id} NOW"
    else:
        return f"{message} for patient {patient_id} (USE THE APPROPRIATE TOOL)"

def _validate_patient_id(patient_id: str) -> bool:
    """Validate that the patient ID is in the correct format"""
    if not patient_id:
        return False
    
    # Check if it's a valid MRN format (adjust based on your system)
    # For now, accept numeric IDs of 4-7 digits
    import re
    pattern = r'^\d{4,7}$'
    return bool(re.match(pattern, patient_id))

@app.on_event("startup")
async def startup_event():
    """Check MCP server health on startup"""
    try:
        is_healthy = await mcp_client.health_check()
        if is_healthy:
            logger.info("MCP server is healthy and ready")
        else:
            logger.warning("MCP server health check failed - service may not be ready")
    except Exception as e:
        logger.error(f"Error checking MCP server health: {e}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up HTTP client on shutdown"""
    try:
        await mcp_client.close()
        logger.info("MCP HTTP client closed successfully")
    except Exception as e:
        logger.error(f"Error closing MCP client: {e}")

if __name__ == "__main__":
   import uvicorn
   port = int(os.getenv("PORT", 3001))
   uvicorn.run(app, host="0.0.0.0", port=port)