import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging
from datetime import datetime

from groq_client import GroqClient
from mcp_executor import MCPExecutor

# Load environment variables from root directory
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
mcp_executor = MCPExecutor(
    mcp_server_path=os.getenv("MCP_SERVER_PATH", "../mcp-server-python/main.py")
)

# Define request/response models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversationHistory: List[Message] = []

class ChatResponse(BaseModel):
    response: str
    conversationHistory: List[Message]

# Define tools for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_patients",
            "description": "Search for patients by name, identifier, or other criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Patient name to search for"},
                    "identifier": {"type": "string", "description": "Patient identifier"},
                    "birthDate": {"type": "string", "description": "Birth date (YYYY-MM-DD)"},
                    "gender": {"type": "string", "enum": ["male", "female", "other"]},
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
]

SYSTEM_PROMPT = """You are an EMR (Electronic Medical Records) assistant with access to a FHIR server through tools. You help healthcare providers query patient data, medical records, conditions, medications, and more.

Available tools:
- search_patients: Search for patients by name, identifier, birth date, or gender
- get_patient_details: Get detailed information about a specific patient
- get_patient_conditions: Get all conditions/diagnoses for a patient
- get_patient_medications: Get current medications for a patient
- get_patient_observations: Get observations (vitals, lab results) for a patient
- get_patient_encounters: Get encounters/visits for a patient
- get_patient_allergies: Get allergy information for a patient

When users ask questions:
1. Understand their intent and determine which tools to use
2. Use the appropriate tools to query the FHIR server
3. Present the information in a clear, clinically relevant format
4. Maintain patient privacy and HIPAA compliance
5. If multiple queries are needed, execute them in a logical order

Always be helpful, accurate, and provide relevant medical context when appropriate. Format responses clearly with bullet points or sections when presenting multiple pieces of information."""

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
        
        # Format messages for Groq
        messages = [msg.dict() for msg in request.conversationHistory]
        messages.append({"role": "user", "content": request.message})
        
        # Get initial response from Groq with tools
        initial_response = await groq_client.chat(messages, TOOLS, SYSTEM_PROMPT)
        response_message = initial_response.choices[0].message
        
        # Check if Groq wants to use tools
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            logger.info(f"Executing {len(response_message.tool_calls)} tool calls")
            
            # Execute each tool call
            tool_results = []
            for tool_call in response_message.tool_calls:
                try:
                    result = await mcp_executor.execute_tool(
                        tool_call.function.name,
                        tool_call.function.arguments
                    )
                    
                    tool_results.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call.id,
                    })
                except Exception as e:
                    logger.error(f"Tool execution error for {tool_call.function.name}: {e}")
                    tool_results.append({
                        "role": "tool",
                        "content": f"Error: {str(e)}",
                        "tool_call_id": tool_call.id,
                    })
            
            # Get final response with tool results
            final_messages = messages + [response_message.dict()] + tool_results
            final_response = await groq_client.complete_with_tool_results(final_messages, [])
            final_message = final_response.choices[0].message
            
            return ChatResponse(
                response=final_message.content,
                conversationHistory=messages + [
                    Message(role="assistant", content=final_message.content)
                ]
            )
        else:
            # No tools needed, return direct response
            return ChatResponse(
                response=response_message.content,
                conversationHistory=messages + [
                    Message(role="assistant", content=response_message.content)
                ]
            )
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)