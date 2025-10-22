"""
LangChain-based chat service with strict tool enforcement and anti-hallucination measures
"""
import logging
from typing import Tuple, Optional

# LangChain message types imported locally where needed
from langchain_groq import ChatGroq

from app.config import settings
from app.services.session_service import SessionService
from app.services.langchain import (
    QueryClassificationService, 
    EMRAgentFactory
)
from app.services.langchain.tools_async import create_async_emr_tools
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)

class LangChainChatService:
    """Enhanced chat service using LangChain with strict tool enforcement"""
    
    def __init__(self, mcp_client: HTTPMCPClient, session_service: SessionService):
        self.session_service = session_service
        
        # Initialize LangChain Groq LLM with valid Groq model
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model="moonshotai/kimi-k2-instruct",  # Valid Groq model with tool support
            temperature=0,  # Deterministic for medical data
            max_retries=3,
        )
        
        # Initialize modular components
        self.query_classifier = QueryClassificationService(self.llm)
        
        # Create async tools
        tools = create_async_emr_tools(mcp_client)
        
        # Create agent executor with async tools
        agent_factory = EMRAgentFactory(self.llm, tools)
        self.agent_executor = agent_factory.create_agent_executor()
        self.tools = tools  # Store for agent invocation
    
    async def process_chat(self, message: str, patient_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Process chat with strict tool enforcement"""
        
        logger.info(f"LangChain processing: message='{message}', patient_id='{patient_id}'")
        
        # Get patient session
        current_patient_id, session = await self.session_service.get_patient_session(patient_id)
        
        # Classify query using the new modular service
        classification = await self.query_classifier.should_use_tools(message, current_patient_id)
        logger.info(f"Query classification: {classification}")
        
        # Build context with patient ID and current date
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        context_parts = []
        if current_patient_id:
            context_parts.append(f"Patient ID {current_patient_id} is selected")
        context_parts.append(f"Today's date is {current_date}")

        context = ". ".join(context_parts)
        full_message = f"{context}. {message}"
        
        # Prepare chat history from session
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        chat_history = []

        # Load session history into chat messages
        for msg in session.history[-settings.MAX_CONVERSATION_HISTORY:]:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))

        logger.info(f"Chat history loaded: {len(chat_history)} messages")
        if chat_history:
            logger.info(f"Last message in history: {chat_history[-1].content[:100] if chat_history else 'None'}...")
        
        # Process based on classification
        if classification.requires_tools and not current_patient_id:
            response = "I need a patient ID to retrieve medical information. Please provide the patient ID or search for a patient first."
        elif classification.requires_tools:
            # Force tool usage for medical queries
            try:
                # Pass ONLY user messages for context understanding
                # This allows follow-up questions like "and the most recent one?" to work
                # But prevents the agent from answering based on previous assistant responses
                from langchain_core.messages import HumanMessage

                recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
                context_history = [msg for msg in recent_history if isinstance(msg, HumanMessage)]

                logger.info(f"🔧 Running agent with {len(context_history)} user messages for context")

                result = await self.agent_executor.ainvoke({
                    "input": full_message,
                    "chat_history": context_history  # ✅ Only user messages
                })

                # Check if tools were actually used
                intermediate_steps = result.get("intermediate_steps", [])
                logger.info(f"Agent result keys: {result.keys()}")
                logger.info(f"Agent result: output='{result.get('output')[:200] if result.get('output') else None}...', intermediate_steps_count={len(intermediate_steps)}")

                # Log detailed intermediate steps info
                if intermediate_steps:
                    for i, step in enumerate(intermediate_steps):
                        logger.info(f"  Step {i}: tool={step[0].tool if hasattr(step[0], 'tool') else 'unknown'}, action={type(step[0]).__name__}")
                else:
                    logger.warning(f"⚠️  NO INTERMEDIATE STEPS - Agent may have used chat history instead of tools!")

                # STRICT CHECK: Only accept if tools were actually called
                if intermediate_steps and len(intermediate_steps) > 0:
                    # Tools were called - this is real data
                    logger.info(f"✅ Tools were called: {[step[0].tool for step in intermediate_steps]}")
                    response = result["output"]
                elif "Agent stopped due to iteration limit" in result.get("output", ""):
                    # Agent hit iteration limit - provide helpful message
                    logger.warning("Agent hit iteration limit - providing fallback response")
                    response = f"I'm having trouble processing this complex request. Let me try to get the patient information for ID {current_patient_id}. Please try asking for specific information like 'show patient details' or 'show medications' for better results."
                else:
                    # Tools weren't used - force error response
                    logger.warning("Tools not used for medical query - forcing safe response")
                    response = "I cannot provide medical information without accessing the patient's records. Please let me retrieve the data from the EMR system."
                    
            except Exception as e:
                logger.error(f"Agent execution error: {e}")
                response = "I encountered an error while retrieving the medical data. Please try again."
        else:
            # Non-medical query - safe to respond without tools, include chat history
            messages = [
                SystemMessage(content="You are a helpful EMR assistant. You can answer general questions and refer to previous conversations. For medical data retrieval, you would need to use tools, but for general conversation you can respond normally.")
            ]

            # Add chat history
            messages.extend(chat_history)

            # Add current message WITH context (date + patient ID)
            messages.append(HumanMessage(content=full_message))  # ✅ Use full_message with date context!

            # Debug: Log what we're sending to LLM
            logger.info(f"Sending to LLM: {len(messages)} messages")
            for i, msg in enumerate(messages):
                logger.info(f"  Message {i}: {type(msg).__name__} - {str(msg.content)[:100]}...")

            response = await self.llm.ainvoke(messages)
            response = response.content
        
        # Update session history
        if current_patient_id:
            await self.session_service.add_to_history(current_patient_id, message, response)
        
        return response, current_patient_id