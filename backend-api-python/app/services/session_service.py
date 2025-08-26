"""
Session management service
Handles patient-scoped conversation sessions
"""
from datetime import datetime
from typing import Optional, Dict, Tuple
from abc import ABC, abstractmethod

from app.models import SessionData
from app.config import settings

class SessionStore(ABC):
    """Abstract base class for session storage"""
    
    @abstractmethod
    async def get_session(self, session_key: str) -> Optional[SessionData]:
        pass
    
    @abstractmethod
    async def set_session(self, session_key: str, session_data: SessionData) -> None:
        pass
    
    @abstractmethod
    async def delete_session(self, session_key: str) -> bool:
        pass

class InMemorySessionStore(SessionStore):
    """In-memory session storage (development/testing)"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
    
    async def get_session(self, session_key: str) -> Optional[SessionData]:
        return self._sessions.get(session_key)
    
    async def set_session(self, session_key: str, session_data: SessionData) -> None:
        self._sessions[session_key] = session_data
    
    async def delete_session(self, session_key: str) -> bool:
        if session_key in self._sessions:
            del self._sessions[session_key]
            return True
        return False

class RedisSessionStore(SessionStore):
    """Redis session storage (production)"""
    
    def __init__(self, redis_url: str):
        # TODO: Implement Redis storage
        raise NotImplementedError("Redis storage not implemented yet")

class SessionService:
    """Service for managing patient-scoped sessions"""
    
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store
    
    async def get_patient_session(self, patient_id: Optional[str]) -> Tuple[Optional[str], SessionData]:
        """Get or create session for specific patient"""
        if not patient_id:
            # Return empty session for general queries without patient context
            return None, SessionData(
                history=[],
                patient_id=None,
                created_at=datetime.utcnow().isoformat(),
                last_accessed=datetime.utcnow().isoformat()
            )
        
        session_key = f"patient_{patient_id}"
        session_data = await self.session_store.get_session(session_key)
        
        if not session_data:
            session_data = SessionData(
                history=[],
                patient_id=patient_id,
                created_at=datetime.utcnow().isoformat(),
                last_accessed=datetime.utcnow().isoformat()
            )
            await self.session_store.set_session(session_key, session_data)
        else:
            # Update last accessed time
            session_data.last_accessed = datetime.utcnow().isoformat()
            await self.session_store.set_session(session_key, session_data)
        
        return patient_id, session_data
    
    async def add_to_history(self, patient_id: str, user_message: str, assistant_response: str):
        """Add conversation to patient session history"""
        session_key = f"patient_{patient_id}"
        session_data = await self.session_store.get_session(session_key)
        
        if session_data:
            session_data.history.extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ])
            
            # Keep session size manageable
            if len(session_data.history) > settings.MAX_CONVERSATION_HISTORY:
                session_data.history = session_data.history[-settings.MAX_CONVERSATION_HISTORY:]
            
            session_data.last_accessed = datetime.utcnow().isoformat()
            await self.session_store.set_session(session_key, session_data)
    
    async def clear_patient_session(self, patient_id: str) -> bool:
        """Clear conversation history for a specific patient"""
        session_key = f"patient_{patient_id}"
        return await self.session_store.delete_session(session_key)