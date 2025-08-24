"""
Configuration management for EMR Backend API
Reads from .env file in project root
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from project root
root_dir = Path(__file__).parent.parent.parent
load_dotenv(root_dir / '.env')

class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "EMR Backend API"
    API_VERSION: str = "4.0.0"
    PORT: int = 8004
    API_HOST: str = "10.7.1.9"
    LOG_LEVEL: str = "info"
    
    # External Services (from .env)
    GROQ_API_KEY: str
    FHIR_SERVER_URL: str = "http://10.201.205.101:8007/"
    FHIR_AUTH_TOKEN: Optional[str] = None
    FHIR_USERNAME: Optional[str] = None
    FHIR_PASSWORD: Optional[str] = None
    
    # MCP Server (auto-constructed from env)
    MCP_SERVER_URL: str = "http://10.7.1.9:8888"
    
    # CORS Settings (from .env)
    CORS_ORIGIN: str = "http://10.7.1.9:3004"
    
    # Frontend (from .env)
    VITE_API_URL: str = "http://10.7.1.9:8004"
    
    # Production Settings
    WORKERS: int = 1
    SESSION_CLEANUP_INTERVAL: int = 3600  # 1 hour
    MAX_CONVERSATION_HISTORY: int = 10
    
    # Redis for production session storage (optional)
    REDIS_URL: Optional[str] = None
    
    @property
    def cors_origins(self) -> List[str]:
        """Convert CORS_ORIGIN to list for FastAPI"""
        return [self.CORS_ORIGIN]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Validate required settings
if not settings.GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is required in .env file")