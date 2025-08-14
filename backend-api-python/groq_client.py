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
            # Check if this is a tool result response (no tools needed)
            has_tool_results = any(msg.get('role') == 'tool' for msg in messages[-3:])
            
            # Analyze if the query needs tools
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '').lower()
                    break
            
            # Check if this is a follow-up query that needs tools
            needs_forced_tools = self._is_medical_follow_up(last_user_msg, messages)
            
            # Build the request payload
            payload = {
                "model": "moonshotai/kimi-k2-instruct",
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            # If tools are provided and this isn't a response with tool results
            if tools and not has_tool_results:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"  # Groq only supports 'auto'
                
                if needs_forced_tools:
                    logger.info("Detected follow-up query that needs tools")
                else:
                    logger.info("Providing tools to LLM for decision")
            else:
                logger.info("Generating response without tools (tool results present)")
            
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
        """Determine if query needs tools - now more permissive for follow-ups"""
        query_lower = query.lower().strip()
        
        # Only skip tools for very clear greetings
        pure_greetings = [
            r'^(hi|hello|hey|good morning|good afternoon|goodbye|bye)$',
            r'^(thank you|thanks|ok|okay)$',
        ]
        
        for pattern in pure_greetings:
            if re.match(pattern, query_lower):
                return False
        
        # IMPORTANT: Follow-up patterns that NEED tools
        follow_up_patterns = [
            r'\btheir\b',  # "their medications", "their conditions"
            r'\babout\b',  # "what about..."
            r'\band\b.*\b(information|details|data)\b',  # "and their information"
            r'\balso\b',  # "also show me"
            r'\bmore\b',  # "more details"
        ]
        
        for pattern in follow_up_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Follow-up query detected with pattern: {pattern}")
                return True
        
        # Medical patterns
        medical_patterns = [
            r'\bpatient\b', r'\bmedical\b', r'\bconditions?\b', r'\bdiagnos\w+\b',
            r'\bmedications?\b', r'\bobservations?\b', r'\ballerg\w+\b',
            r'\bvitals?\b', r'\bencounters?\b', r'\bvisits?\b', r'\blab\b',
            r'\bresults?\b', r'\btests?\b', r'\bblood\b', r'\bpressure\b',
            r'\bweight\b', r'\bheight\b', r'\bdiseases?\b', r'\billness\b',
            r'\bprescription\b', r'\bdrugs?\b', r'\bmedicines?\b', r'\bpills?\b',
            r'\binformation\b', r'\bdetails?\b', r'\bdata\b',
        ]
        
        for pattern in medical_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Medical query detected with pattern: {pattern}")
                return True
        
        # Questions almost always need tools
        question_patterns = [
            r'\b(what|how|when|where|which|who|show|display|get|tell|give)\b'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, query_lower):
                logger.info("Question detected - providing tools")
                return True
        
        # Default to true for safety - let LLM decide
        logger.info("Uncertain query - providing tools to be safe")
        return True
    
    def _looks_like_json_data(self, text: str) -> bool:
        """Check if text looks like JSON tool result data"""
        text = text.strip()
        # Check if it starts with JSON-like structure
        if text.startswith('{') and '"total":' in text and '"observations":' in text:
            return True
        if text.startswith('{') and len(text) > 200:  # Large JSON objects
            return True
        return False
    
    def _is_medical_follow_up(self, query: str, messages: List[Dict[str, Any]]) -> bool:
        """Determine if this is a follow-up query that needs tools"""
        query_lower = query.lower().strip()
        
        # Check for pronouns and references that indicate follow-up
        follow_up_indicators = [
            'their', 'his', 'her', 'the patient', 'this patient',
            'what about', 'and', 'also', 'show me more',
            'conditions', 'medications', 'medication', 'drugs',
            'observations', 'allergies', 'information', 'details',
            'vitals', 'labs', 'results'
        ]
        
        for indicator in follow_up_indicators:
            if indicator in query_lower:
                # Check if we have a patient context in recent messages
                for msg in messages[-10:]:
                    content = str(msg.get('content', '')).lower()
                    if 'patient' in content and any(char.isdigit() for char in content):
                        logger.info(f"Follow-up query detected: '{indicator}' found with patient context")
                        return True
        
        return False