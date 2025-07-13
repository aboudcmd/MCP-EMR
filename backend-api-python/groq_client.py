import logging
from typing import List, Dict, Any
from groq import Groq
import json

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
    
    async def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str):
        """Send chat request to Groq with tools"""
        try:
            # Build the request payload
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0,
                "max_tokens": 1024,
            }
            
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