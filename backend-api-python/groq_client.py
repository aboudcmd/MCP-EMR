import logging
from typing import List, Dict, Any
from groq import Groq
from semantic_router import SemanticQueryRouter

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        # Initialize semantic router for intelligent query classification
        try:
            self.semantic_router = SemanticQueryRouter(similarity_threshold=0.25)
            logger.info("Semantic query router initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize semantic router, falling back to keywords: {e}")
            self.semantic_router = None
    
    async def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str):
        """Send chat request to Groq with tools"""
        try:
            # Intelligent query analysis
            needs_tools = False
            if messages:
                last_user_msg = messages[-1].get('content', '')
                
                if self.semantic_router:
                    # Use semantic similarity for tool detection
                    needs_tools = self.semantic_router.needs_tools(last_user_msg)
                    if needs_tools:
                        best_tools = self.semantic_router.get_best_tools(last_user_msg, top_k=3)
                        tool_names = [tool[0] for tool in best_tools]
                        logger.info(f"Semantic analysis suggests tools needed: {tool_names}")
                    else:
                        logger.info("Semantic analysis: conversational query, no tools needed")
                else:
                    # Fallback: assume tools needed for safety if semantic router fails
                    needs_tools = True
                    logger.warning("Semantic router unavailable - defaulting to tools enabled")
            
            # Build the request payload
            payload = {
                "model": "moonshotai/kimi-k2-instruct",
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            # Only add tools if they're provided and the query needs them
            if tools and needs_tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                logger.info("Tools provided to LLM based on query analysis")
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
                "model": "moonshotai/kimi-k2-instruct",
                "messages": messages + tool_results,
                "temperature": 0,
                "max_tokens": 1024,
            }
            
            response = self.client.chat.completions.create(**payload)
            return response
            
        except Exception as e:
            logger.error(f"Groq completion error: {e}")
            raise