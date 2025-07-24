import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
    
    async def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str):
        """Send chat request to Groq with tools"""
        try:
            # Check if the last user message likely needs data
            if messages:
                last_user_msg = messages[-1].get('content', '').lower()
                data_keywords = ['show', 'get', 'what', 'list', 'find', 'medical', 'vitals', 
                               'conditions', 'medications', 'allergies', 'summary', 'history',
                               'all patients', 'patients', 'records']
                
                if any(keyword in last_user_msg for keyword in data_keywords):
                    logger.info("Query likely needs tool usage")
            
            # Build the request payload
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            # Only add tools if they're provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**payload)
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    async def complete_with_tool_results(self, messages: List[Dict[str, Any]], tool_results: List[Dict[str, Any]]):
        """Complete conversation with tool results"""
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages + tool_results,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            response = self.client.chat.completions.create(**payload)
            return response
            
        except Exception as e:
            logger.error(f"Groq completion error: {e}")
            raise