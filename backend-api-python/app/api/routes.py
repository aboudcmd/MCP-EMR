"""
API routes for EMR Backend
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from app.models import ChatRequest, ChatResponse, SessionClearResponse, HealthResponse
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.dependencies import get_chat_service, get_session_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.API_VERSION
    )

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Handle chat requests with patient-scoped sessions"""
    try:
        logger.info(f"Chat request: message='{request.message}', patient_id='{request.patientId}'")
        
        response_content, patient_id = await chat_service.process_chat(
            message=request.message,
            patient_id=request.patientId
        )
        
        logger.info("Chat response generated successfully")
        
        return ChatResponse(
            response=response_content,
            patientId=patient_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/patient/{patient_id}/session", response_model=SessionClearResponse)
async def clear_patient_session(
    patient_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Clear conversation history for a specific patient"""
    try:
        success = await session_service.clear_patient_session(patient_id)
        
        if success:
            logger.info(f"Session for patient {patient_id} cleared")
            return SessionClearResponse(
                status="patient session cleared",
                patientId=patient_id
            )
        else:
            return SessionClearResponse(
                status="patient session not found",
                patientId=patient_id
            )
            
    except Exception as e:
        logger.error(f"Error clearing session for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))