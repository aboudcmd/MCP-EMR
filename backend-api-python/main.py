# backend-api-python/main.py
import os
import json  # <-- This import was missing!
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from groq_client import GroqClient
from mcp_executor import MCPExecutor

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
mcp_executor = MCPExecutor(
    mcp_server_path=os.getenv("MCP_SERVER_PATH", "../mcp-server-python/main.py")
)

# Request/Response models
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
            "description": "Search for patients by name, identifier, or other criteria. Leave parameters empty to get all patients.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Patient name to search for"},
                    "identifier": {"type": "string", "description": "Patient identifier/MRN"},
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

SYSTEM_PROMPT = """You are an EMR (Electronic Medical Records) assistant with access to a FHIR server through tools.

CRITICAL RULES:
1. NEVER make up or hallucinate patient data
2. ALWAYS use tools to retrieve actual data from the FHIR server
3. If you need patient information, you MUST call the appropriate tool and wait for results
4. Only provide information that comes from tool results
5. If no data is found, say "No data found" rather than making up information

When users ask for medical information:
- First, identify what data is needed
- Call the appropriate tool(s)
- Wait for the tool results
- ONLY use the data from tool results in your response
- If the tool returns no data, inform the user that no data was found

Remember: You must NEVER provide medical data unless it comes from a tool result. Always be helpful and format responses clearly."""

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
        
        # Build conversation history
        messages = []
        
        # Add system prompt
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
        
        # Add conversation history
        for msg in request.conversationHistory:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Get initial response from Groq with tools
        initial_response = await groq_client.chat(messages, TOOLS, SYSTEM_PROMPT)
        response_message = initial_response.choices[0].message
        
        # Check if Groq wants to use tools
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            logger.info(f"Executing {len(response_message.tool_calls)} tool calls")
            
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
                    
                    # Execute the tool
                    result = await mcp_executor.execute_tool(
                        tool_call.function.name,
                        tool_call.function.arguments
                    )
                    
                    # Add tool result to messages
                    # Add tool result to messages
                    tool_result_msg = {
                        "role": "tool",
                        "content": json.dumps(result),  # Convert result to JSON string
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
           # Important: Don't pass tools this time to force response generation
            final_response = await groq_client.chat(messages, [], SYSTEM_PROMPT)
            final_message = final_response.choices[0].message
           
           # Return the response
            return ChatResponse(
                response=final_message.content,
                conversationHistory=request.conversationHistory + [
                    Message(role="user", content=request.message),
                    Message(role="assistant", content=final_message.content)
                ]
            )
        else:
            # No tools needed, return direct response
            return ChatResponse(
                response=response_message.content,
                conversationHistory=request.conversationHistory + [
                    Message(role="user", content=request.message),
                    Message(role="assistant", content=response_message.content)
                ]
            )
           
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")

if __name__ == "__main__":
   import uvicorn
   port = int(os.getenv("PORT", 3001))
   uvicorn.run(app, host="0.0.0.0", port=port)