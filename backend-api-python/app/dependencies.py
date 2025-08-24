"""
Dependency injection for FastAPI
"""
import logging
from functools import lru_cache

from app.config import settings
from app.services.session_service import SessionService, InMemorySessionStore
from app.services.chat_service import ChatService
from groq_client import GroqClient
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)

# Global instances (singletons)
_groq_client = None
_mcp_client = None
_session_service = None
_chat_service = None

@lru_cache()
def get_groq_client() -> GroqClient:
    """Get Groq client instance"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient(settings.GROQ_API_KEY)
        logger.info("Groq client initialized")
    return _groq_client

@lru_cache()
def get_mcp_client() -> HTTPMCPClient:
    """Get MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = HTTPMCPClient(mcp_server_url=settings.MCP_SERVER_URL)
        logger.info(f"MCP client initialized: {settings.MCP_SERVER_URL}")
    return _mcp_client

@lru_cache()
def get_session_service() -> SessionService:
    """Get session service instance"""
    global _session_service
    if _session_service is None:
        # Use in-memory storage for now (TODO: implement Redis for production)
        session_store = InMemorySessionStore()
        _session_service = SessionService(session_store)
        logger.info("Session service initialized with in-memory store")
    return _session_service

@lru_cache()
def get_chat_service() -> ChatService:
    """Get chat service instance"""
    global _chat_service
    if _chat_service is None:
        groq_client = get_groq_client()
        mcp_client = get_mcp_client()
        session_service = get_session_service()
        _chat_service = ChatService(groq_client, mcp_client, session_service)
        logger.info("Chat service initialized")
    return _chat_service

async def startup_dependencies():
    """Initialize and health check dependencies on startup"""
    try:
        mcp_client = get_mcp_client()
        is_healthy = await mcp_client.health_check()
        if is_healthy:
            logger.info("✅ MCP server is healthy")
        else:
            logger.warning("⚠️ MCP server health check failed")
    except Exception as e:
        logger.error(f"❌ Error checking MCP server: {e}")

async def shutdown_dependencies():
    """Cleanup dependencies on shutdown"""
    try:
        if _mcp_client:
            await _mcp_client.close()
        logger.info("✅ Dependencies cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")