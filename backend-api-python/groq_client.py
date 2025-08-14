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
            # Intelligent query analysis - only for user messages, not tool results
            needs_tools = False
            force_specific_tool = None
            
            if messages and tools:  # Only analyze if tools are provided
                last_user_msg = messages[-1].get('content', '')
                last_user_role = messages[-1].get('role', '')
                
                # Skip semantic analysis for tool results or JSON data
                if last_user_role == 'user' and not self._looks_like_json_data(last_user_msg):
                    if self.semantic_router:
                        # Use semantic similarity for tool detection
                        needs_tools = self.semantic_router.needs_tools(last_user_msg)
                        if needs_tools:
                            best_tools = self.semantic_router.get_best_tools(last_user_msg, top_k=3)
                            tool_names = [tool[0] for tool in best_tools]
                            logger.info(f"Semantic analysis suggests tools needed: {tool_names}")
                            
                            # CRITICAL FIX: Force tool for high confidence medical queries
                            if best_tools and best_tools[0][1] > 0.35:  # Lowered threshold
                                force_specific_tool = best_tools[0][0]
                                logger.info(f"FORCING tool {force_specific_tool} with confidence {best_tools[0][1]:.3f}")
                        else:
                            logger.info("Semantic analysis: conversational query, no tools needed")
                    else:
                        # Fallback: assume tools needed for safety if semantic router fails
                        needs_tools = True
                        logger.warning("Semantic router unavailable - defaulting to tools enabled")
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
                if force_specific_tool:
                    # AGGRESSIVE FORCING: Only provide the ONE tool we want to use
                    forced_tool = next((t for t in tools if t["function"]["name"] == force_specific_tool), None)
                    if forced_tool:
                        payload["tools"] = [forced_tool]  # Only give it one option
                        payload["tool_choice"] = "required"  # Use "required" instead of specific function
                        logger.info(f"AGGRESSIVE FORCE: Only providing {force_specific_tool} tool with 'required' choice")
                    else:
                        payload["tools"] = tools
                        payload["tool_choice"] = "auto"
                elif self.semantic_router:
                    # Filter tools based on semantic analysis
                    best_tools = self.semantic_router.get_best_tools(last_user_msg, top_k=3)
                    tool_names = [tool[0] for tool in best_tools]
                    filtered_tools = [tool for tool in tools if tool["function"]["name"] in tool_names]
                    if filtered_tools:
                        payload["tools"] = filtered_tools
                        payload["tool_choice"] = "auto"
                        logger.info(f"Providing filtered tools: {[t['function']['name'] for t in filtered_tools]}")
                    else:
                        payload["tools"] = tools
                        payload["tool_choice"] = "auto"
                else:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                    logger.info("Tools provided to LLM based on query analysis")
            elif tools and not needs_tools:
                logger.info("Tools available but withheld - query appears conversational")
            else:
                logger.info("No tools available or query doesn't need tools")
            
            response = self.client.chat.completions.create(**payload)
            
            # VALIDATION: Check if tool was actually called when forced
            if force_specific_tool and hasattr(response.choices[0].message, 'tool_calls'):
                if not response.choices[0].message.tool_calls:
                    logger.warning(f"WARNING: Tool {force_specific_tool} was forced but LLM didn't call it!")
                    # Retry with even more aggressive prompting
                    messages_with_instruction = messages.copy()
                    messages_with_instruction[-1]["content"] = f"USE THE {force_specific_tool} TOOL TO ANSWER THIS: {last_user_msg}"
                    payload["messages"] = messages_with_instruction
                    logger.info("Retrying with explicit tool instruction in message")
                    response = self.client.chat.completions.create(**payload)
            
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # If forced tool call failed, try again with auto choice  
            if "tool_use_failed" in str(e) and "tool_choice" in payload:
                logger.warning("Forced tool call failed, retrying with auto choice")
                payload["tool_choice"] = "auto"
                try:
                    response = self.client.chat.completions.create(**payload)
                    return response
                except Exception as retry_e:
                    logger.error(f"Retry with auto choice also failed: {retry_e}")
                    raise retry_e
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
    
    def _looks_like_json_data(self, text: str) -> bool:
        """Check if text looks like JSON tool result data"""
        text = text.strip()
        # Check if it starts with JSON-like structure
        if text.startswith('{') and '"total":' in text and '"observations":' in text:
            return True
        if text.startswith('{') and len(text) > 200:  # Large JSON objects
            return True
        return False