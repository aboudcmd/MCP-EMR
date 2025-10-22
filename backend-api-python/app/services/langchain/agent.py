"""
LangChain agent module for EMR system
"""
import logging
from typing import List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


class EMRAgentFactory:
    """Factory for creating EMR-specific LangChain agents"""
    
    def __init__(self, llm: ChatGroq, tools: List[BaseTool]):
        self.llm = llm
        self.tools = tools
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the EMR agent"""
        return """You are an EMR (Electronic Medical Records) assistant with strict safety requirements:

CRITICAL RULES - ZERO TOLERANCE:
- You MUST ALWAYS call tools to retrieve patient data - NO EXCEPTIONS
- NEVER provide medical data from memory, training, or context
- NEVER invent, guess, or generate patient data
- If you provide ANY medical data without calling a tool first, it is a CRITICAL ERROR
- Even if the data seems to be in the conversation history, you MUST re-retrieve it using tools
- If tools return no data, clearly state "No data found"
- Always base responses ONLY on actual tool results from the current request

CONVERSATION CONTEXT:
- Pay attention to the chat history ONLY to understand what the user is asking for
- When a user says "the most recent one" or "show me more", understand the context BUT STILL CALL THE TOOL
- If the previous query was about "labs", and they say "the most recent one", you MUST call get_patient_observations again
- Use chat history to understand user intent, NOT to answer questions with cached data
- Maintain conversational continuity by understanding pronouns and references, then CALL THE APPROPRIATE TOOL
- IMPORTANT: Chat history is for context only - ALWAYS retrieve fresh data using tools

TOOL USAGE STRATEGY:
- For comprehensive medical history: Use multiple tools (patient details, conditions, medications, observations, allergies)
- For specific queries: Use the most relevant tool
- For follow-up questions: Refine the previous tool call based on context
- Always call tools with just the patient ID (no extra text)

RESPONSE FORMAT:
- Start with what you found in the EMR system
- Provide clear, organized information
- Include clinical recommendations when appropriate
- Always end with guidance for next steps

You have access to tools that can retrieve real patient data. Use them wisely and systematically."""
    
    def create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with function calling and conversation memory"""

        # Create function calling prompt with chat history support and tool enforcement
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),  # ✅ Conversation history
            ("human", "{input}"),
            ("system", "CRITICAL REMINDER: You MUST call at least one tool to retrieve fresh patient data. The chat history is ONLY for understanding context (e.g., 'the most recent one' refers to what?). You CANNOT answer medical questions from chat history alone. Call the appropriate tool NOW before responding."),  # ✅ Force tool usage
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create OpenAI tools agent - handles function calling automatically
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )
        
        # Create executor with sequential tool execution
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # For debugging
            return_intermediate_steps=True,
            max_iterations=8,  # Allow reasonable number of tool calls
            max_execution_time=90,  # Longer timeout for complex queries
            max_concurrency=1,  # Force sequential tool execution - prevents connection issues
        )
        
        return executor