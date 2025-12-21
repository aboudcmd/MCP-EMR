"""
API routes aggregator for EMR Backend
Combines all route modules into a single router
"""
import logging
from datetime import datetime
from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse

# Import sub-routers
from app.api.chat_routes import router as chat_router
from app.api.patient_routes import router as patient_router

logger = logging.getLogger(__name__)

# Main router that aggregates all routes
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.API_VERSION
    )


# Include sub-routers
router.include_router(chat_router)
router.include_router(patient_router)
