"""
Simplified Groq client - let the LLM decide naturally
"""
import logging
import sys
from typing import List, Dict, Any
from groq import Groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "moonshotai/kimi-k2-instruct"  # More reliable model
        logger.info(f"GroqClient initialized with model: {self.model}")
    
    async def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str):
        """Send chat request to Groq"""
        try:
            logger.info(f"Groq request: {len(messages)} messages, {len(tools)} tools available")
            
            # Build request
            request = {
                "model": self.model,
                "messages": messages,
                "temperature": 0,  # Low temperature for consistency
                "max_tokens": 2048,
            }
            
            # Add tools if provided and not processing tool results
            has_tool_results = any(msg.get('role') == 'tool' for msg in messages[-5:])
            
            if tools and not has_tool_results:
                request["tools"] = tools
                request["tool_choice"] = "auto"  # Let LLM decide
                logger.info("Tools provided to LLM")
            else:
                logger.info("No tools provided (processing results)" if has_tool_results else "No tools available")
            
            # Make API call
            response = self.client.chat.completions.create(**request)
            
            # Log response type
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_names = [tc.function.name for tc in response.choices[0].message.tool_calls]
                logger.info(f"✅ LLM using tools: {tool_names}")
            else:
                logger.info("LLM responded without tools")
            
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}", exc_info=True)
            raise