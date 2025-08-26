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
    EMRToolsFactory, 
    EMRAgentFactory,
    MedicalQueryClassifier
)
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
        tools_factory = EMRToolsFactory(mcp_client)
        tools = tools_factory.create_tools()
        
        # Create agent executor
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
        
        # Build context with patient ID
        context = f"Patient ID {current_patient_id} is selected" if current_patient_id else "No patient selected"
        full_message = f"{context}. {message}" if current_patient_id else message
        
        # Prepare chat history from session
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        chat_history = []
        
        # Load session history into chat messages
        for msg in session.history[-settings.MAX_CONVERSATION_HISTORY:]:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))
        
        # Process based on classification
        if classification.requires_tools and not current_patient_id:
            response = "I need a patient ID to retrieve medical information. Please provide the patient ID or search for a patient first."
        elif classification.requires_tools:
            # Force tool usage for medical queries
            try:
                # Run agent with tool enforcement
                result = await self.agent_executor.ainvoke({
                    "input": full_message,
                    "tools": self.tools,
                    "tool_names": [tool.name for tool in self.tools]
                })
                
                # Check if tools were actually used
                intermediate_steps = result.get("intermediate_steps", [])
                logger.info(f"Agent result: output='{result.get('output')}', intermediate_steps_count={len(intermediate_steps)}")
                
                if intermediate_steps:
                    response = result["output"]
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
            
            # Add current message
            messages.append(HumanMessage(content=message))
            
            response = await self.llm.ainvoke(messages)
            response = response.content
        
        # Update session history
        if current_patient_id:
            await self.session_service.add_to_history(current_patient_id, message, response)
        
        return response, current_patient_id