# backend-api-python/main_v2.py
"""
Production-ready EMR Backend API with proper MCP integration
No keyword matching, no forced tool usage - let the LLM work naturally
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys

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
        logging.StreamHandler(sys.stdout)  # Force stdout
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Initialize FastAPI app
app = FastAPI(title="EMR Backend API", version="2.0.0")

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
        description="Patient context for the conversation"
    )
    conversationHistory: List[Message] = Field(
        default=[],
        description="Previous messages for context"
    )

class ChatResponse(BaseModel):
    response: str
    conversationHistory: List[Message]

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

# Simplified, natural system prompt
SYSTEM_PROMPT = """You are an EMR (Electronic Medical Records) assistant with access to patient data through various tools.

When users ask about medical information, use the appropriate tools to retrieve accurate, up-to-date data from the EMR system.

Important guidelines:
- Always use tools to retrieve medical data rather than relying on general knowledge
- If a tool returns no data, inform the user clearly
- Present information in a clear, organized manner
- Maintain patient privacy and confidentiality

You have access to tools for searching patients, retrieving conditions, medications, observations, allergies, and other medical data."""

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with improved architecture"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"NEW CHAT REQUEST")
        logger.info(f"Message: {request.message}")
        logger.info(f"Patient ID: {request.patientId}")
        logger.info(f"History length: {len(request.conversationHistory)}")
        logger.info(f"{'='*60}\n")
        
        # Build conversation with context
        messages = []
        
        # Add system prompt with patient context if available
        system_content = SYSTEM_PROMPT
        if request.patientId:
            system_content += f"\n\nCurrent patient context: Patient ID {request.patientId}"
        
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history (limited to prevent token exhaustion)
        MAX_HISTORY = 20
        history = request.conversationHistory[-MAX_HISTORY:] if len(request.conversationHistory) > MAX_HISTORY else request.conversationHistory
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Get LLM response with tools
        logger.info("Calling LLM with tools available...")
        response = await groq_client.chat(messages, TOOLS, SYSTEM_PROMPT)
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
            for tool_call in response_message.tool_calls:
                try:
                    logger.info(f"Executing tool: {tool_call.function.name}")
                    
                    # Parse arguments
                    args = json.loads(tool_call.function.arguments)
                    
                    # If no patient ID in args but we have context, add it
                    if request.patientId and 'patientId' not in args and tool_call.function.name != 'search_patients':
                        args['patientId'] = request.patientId
                    
                    # Execute tool
                    result = await mcp_client.execute_tool(
                        tool_call.function.name,
                        args
                    )
                    
                    logger.info(f"Tool {tool_call.function.name} completed")
                    
                    # Add tool result
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result) if not isinstance(result, str) else result,
                        "tool_call_id": tool_call.id,
                    })
                    
                except Exception as e:
                    logger.error(f"Tool error: {e}")
                    messages.append({
                        "role": "tool",
                        "content": json.dumps({"error": str(e)}),
                        "tool_call_id": tool_call.id,
                    })
            
            # Get final response from LLM
            logger.info("Getting final response from LLM...")
            final_response = await groq_client.chat(messages, [], SYSTEM_PROMPT)
            final_content = final_response.choices[0].message.content
        else:
            # Direct response without tools
            logger.info("LLM responded without using tools")
            final_content = response_message.content
        
        # Update conversation history
        updated_history = list(request.conversationHistory) + [
            Message(role="user", content=request.message),
            Message(role="assistant", content=final_content)
        ]
        
        logger.info(f"Response generated successfully\n{'='*60}\n")
        
        return ChatResponse(
            response=final_content,
            conversationHistory=updated_history
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting EMR Backend API v2.0...")
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