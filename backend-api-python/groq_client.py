import logging
import re
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        logger.info("GroqClient initialized successfully")
    
    async def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str):
        """Send chat request to Groq with tools"""
        try:
            # Simple pattern-based tool selection
            needs_tools = False
            
            if messages and tools:  # Only analyze if tools are provided
                last_user_msg = messages[-1].get('content', '')
                last_user_role = messages[-1].get('role', '')
                
                # Skip tool analysis for tool results or JSON data
                if last_user_role == 'user' and not self._looks_like_json_data(last_user_msg):
                    needs_tools = self._should_use_tools(last_user_msg)
                    if needs_tools:
                        logger.info("Query requires medical data - providing tools to LLM")
                    else:
                        logger.info("Conversational query detected - no tools needed")
                else:
                    # For final response generation with tool results, don't use tools
                    needs_tools = False
                    logger.info("Generating final response with tool results - no additional tools needed")
            
            # Build the request payload
            payload = {
                "model": "moonshotai/kimi-k2-instruct",  # Changed to more reliable model
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            # Only add tools if they're provided and the query needs them
            if tools and needs_tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                logger.info("Providing all tools to LLM - let LLM choose the appropriate one")
            elif tools and not needs_tools:
                logger.info("Tools available but withheld - query appears conversational")
            else:
                logger.info("No tools available or query doesn't need tools")
            
            response = self.client.chat.completions.create(**payload)
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    async def complete_with_tool_results(self, messages: List[Dict[str, Any]], tool_results: List[Dict[str, Any]]):
        """Complete conversation with tool results"""
        try:
            payload = {
                "model": "moonshotai/kimi-k2-instruct",  # Changed to consistent model
                "messages": messages + tool_results,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            response = self.client.chat.completions.create(**payload)
            return response
            
        except Exception as e:
            logger.error(f"Groq completion error: {e}")
            raise
    
    def _should_use_tools(self, query: str) -> bool:
        """Determine if query needs tools using simple pattern matching"""
        query_lower = query.lower().strip()
        
        # Skip tools for clearly conversational queries
        conversational_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|thank you|thanks|ok|okay|yes|no|bye|goodbye)\b',
            r'^(how are you|what\'s up|how\'s it going)\b',
        ]
        
        for pattern in conversational_patterns:
            if re.match(pattern, query_lower):
                return False
        
        # Use tools for medical/patient queries
        medical_patterns = [
            r'\bpatient\b', r'\bmedical\b', r'\bconditions?\b', r'\bdiagnos\w+\b',
            r'\bmedications?\b', r'\bobservations?\b', r'\ballerg\w+\b',
            r'\bvitals?\b', r'\bencounters?\b', r'\bvisits?\b', r'\blab\b',
            r'\bresults?\b', r'\btests?\b', r'\bblood\b', r'\bpressure\b',
            r'\bweight\b', r'\bheight\b', r'\bdiseases?\b', r'\billness\b',
            r'\bprescription\b', r'\bdrugs?\b', r'\bmedicines?\b', r'\bpills?\b',
            r'\bwhat\b.*\b(condition|medication|vital|allerg|diagnos)\b',
            r'\bshow\b.*\b(patient|medical|condition|medication)\b',
            r'\btell me\b.*\b(about|condition|medication|patient)\b',
            # Arabic patterns
            r'\bمريض\b', r'\bحالة\b', r'\bأدوية\b', r'\bضغط\b', r'\bفحوصات\b'
        ]
        
        for pattern in medical_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Medical query detected with pattern: {pattern}")
                return True
        
        # Default: use tools for questions that might need data
        question_patterns = [
            r'\b(what|how|when|where|which|who|show|display|get|tell me|give me)\b'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, query_lower):
                logger.info("Question detected - providing tools")
                return True
        
        return False
    
    def _looks_like_json_data(self, text: str) -> bool:
        """Check if text looks like JSON tool result data"""
        text = text.strip()
        # Check if it starts with JSON-like structure
        if text.startswith('{') and '"total":' in text and '"observations":' in text:
            return True
        if text.startswith('{') and len(text) > 200:  # Large JSON objects
            return True
        return False