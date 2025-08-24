"""
Pydantic models for EMR Backend API
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

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

class SessionClearResponse(BaseModel):
    status: str
    patientId: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Session models for internal use
class SessionData(BaseModel):
    history: List[Dict[str, str]] = []
    patient_id: Optional[str] = None
    created_at: str
    last_accessed: str