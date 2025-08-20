# backend-api-python/main.py
"""
Production-ready EMR Backend API with session-based conversation management
Anti-hallucination measures and proper logging for frontend integration
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from groq_client import GroqClient
from http_mcp_client import HTTPMCPClient

# Configure logging to ensure immediate output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Override any existing configuration
)

# Set up logger
logger = logging.getLogger(__name__)

# Force all loggers to use our configuration
logging.getLogger().handlers.clear()
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger().setLevel(logging.INFO)

# Load environment variables
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Initialize FastAPI app
app = FastAPI(title="EMR Backend API", version="3.0.0")

# In-memory session storage (replace with Redis/database in production)
sessions = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3004")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
groq_client = GroqClient(os.getenv("GROQ_API_KEY", ""))
mcp_client = HTTPMCPClient(
    mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8888")
)

# Request/Response models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    patientId: Optional[str] = Field(
        default=None,
        description="Patient ID - creates/uses patient-scoped session"
    )

class ChatResponse(BaseModel):
    response: str
    patientId: Optional[str]

# Tool definitions - Clean and semantic, no forcing
TOOLS = [
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

# Anti-hallucination system prompt
SYSTEM_PROMPT = """You are an EMR (Electronic Medical Records) assistant. You MUST follow these rules EXACTLY:

ABSOLUTE REQUIREMENTS - NEVER VIOLATE THESE:
1. NEVER invent, create, or hallucinate ANY patient information
2. NEVER provide patient names, IDs, diagnoses, or any medical data without retrieving it from tools
3. ALWAYS use tools for ANY patient-related query - no exceptions
4. If no patient ID is provided, you MUST ask for it first
5. If tools return empty/no data, you MUST say "No data found" - do not fill in gaps

WHEN RESPONDING:
- For discharge summaries: Only include data that was ACTUALLY retrieved from tools
- For patient queries: Only report what the tools return
- If asked to create documents without patient ID: Say "I need a patient ID to retrieve the necessary information"
- If tools return empty results: Say "No records found for this patient/query"

TOOL USAGE:
- You have access to: search_patients, get_patient_details, get_patient_conditions, get_patient_medications, get_patient_observations, get_patient_allergies
- Use these tools for ALL patient data retrieval
- Never assume or guess patient information

FORBIDDEN ACTIONS:
- Creating fictional patient names or IDs
- Inventing medical diagnoses or conditions
- Making up dates, vital signs, or lab results
- Providing generic medical advice as if it's specific patient data

Remember: Every piece of patient information MUST come from tool responses. If you don't have the data, say so."""

def get_patient_session(patient_id: Optional[str]) -> tuple[Optional[str], dict]:
    """Get or create session for specific patient"""
    if not patient_id:
        # Return empty session for general queries without patient context
        return None, {"history": [], "patient_id": None}
    
    session_key = f"patient_{patient_id}"
    
    if session_key not in sessions:
        sessions[session_key] = {
            "history": [],
            "patient_id": patient_id,
            "created_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Created new session for patient {patient_id}")
    
    return patient_id, sessions[session_key]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with session-based management and anti-hallucination"""
    try:
        print(f"\n{'='*60}", flush=True)
        print(f"NEW CHAT REQUEST", flush=True) 
        print(f"Message: {request.message}", flush=True)
        print(f"Patient ID: {request.patientId}", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"NEW CHAT REQUEST")
        logger.info(f"Message: {request.message}")
        logger.info(f"Patient ID: {request.patientId}")
        logger.info(f"{'='*60}\n")
        
        # Get patient-scoped session
        current_patient_id, session = get_patient_session(request.patientId)
        
        # Build conversation with strict context
        messages = []
        
        # Add system prompt with current patient context
        system_content = SYSTEM_PROMPT
        if current_patient_id:
            system_content += f"\n\nCURRENT CONTEXT: Patient ID {current_patient_id} is selected. Use this ID for all patient-related queries unless a different ID is explicitly mentioned."
        else:
            system_content += "\n\nCURRENT CONTEXT: No patient ID selected. Ask for patient ID before retrieving any medical information."
        
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history from session (server-side managed)
        for msg in session["history"][-10:]:  # Limit history to last 10 messages
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Check if user is asking for patient info without ID
        needs_patient_id = any(keyword in request.message.lower() for keyword in [
            'discharge', 'summary', 'patient', 'medication', 'condition', 
            'diagnosis', 'allergy', 'vital', 'observation'
        ])
        
        if needs_patient_id and not current_patient_id and "search" not in request.message.lower():
            # Immediately ask for patient ID without calling LLM
            response_content = "I need a patient ID to retrieve medical information. Please provide the patient ID or search for a patient first."
        else:
            # Get LLM response with tools
            logger.info("Calling LLM with strict anti-hallucination prompt...")
            response = await groq_client.chat(messages, TOOLS, system_content)
            response_message = response.choices[0].message
            
            # Process tool calls if any
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                logger.info(f"LLM using {len(response_message.tool_calls)} tools")
                
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
                        if current_patient_id and 'patientId' not in args and tool_call.function.name != 'search_patients':
                            args['patientId'] = current_patient_id
                        
                        # Execute tool
                        result = await mcp_client.execute_tool(
                            tool_call.function.name,
                            args
                        )
                        
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
                    # Force a "no data found" response
                    logger.info("All tools returned empty results, enforcing 'no data found' response")
                    response_content = "No data was found in the EMR system for this query. The patient may not have records for the requested information, or the patient ID may not exist in the system."
                else:
                    # Get final response from LLM with tool results
                    logger.info("Getting final response from LLM with tool results...")
                    final_response = await groq_client.chat(messages, [], system_content)
                    response_content = final_response.choices[0].message.content
            else:
                # Direct response without tools
                logger.info("LLM responded without using tools")
                response_content = response_message.content
        
        # Update session history (server-side)
        session["history"].append({"role": "user", "content": request.message})
        session["history"].append({"role": "assistant", "content": response_content})
        
        # Keep session size manageable
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]
        
        logger.info(f"Response generated successfully\n{'='*60}\n")
        
        return ChatResponse(
            response=response_content,
            patientId=current_patient_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/patient/{patient_id}/session")
async def clear_patient_session(patient_id: str):
    """Clear conversation history for a specific patient"""
    session_key = f"patient_{patient_id}"
    if session_key in sessions:
        del sessions[session_key]
        logger.info(f"Session for patient {patient_id} cleared")
        return {"status": "patient session cleared", "patientId": patient_id}
    return {"status": "patient session not found", "patientId": patient_id}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting EMR Backend API v3.0...")
    try:
        is_healthy = await mcp_client.health_check()
        if is_healthy:
            logger.info("✅ MCP server is healthy")
        else:
            logger.warning("⚠️ MCP server health check failed")
    except Exception as e:
        logger.error(f"❌ Error checking MCP server: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down EMR Backend API...")
    try:
        await mcp_client.close()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    logger.info(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)