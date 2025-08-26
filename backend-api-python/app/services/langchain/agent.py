"""
LangChain agent module for EMR system
"""
import logging
from typing import List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


class EMRAgentFactory:
    """Factory for creating EMR-specific LangChain agents"""
    
    def __init__(self, llm: ChatGroq, tools: List[Tool]):
        self.llm = llm
        self.tools = tools
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the EMR agent"""
        return """You are an EMR (Electronic Medical Records) assistant with strict safety requirements:

CRITICAL RULES:
- You MUST use the provided tools for ALL medical information
- NEVER invent or guess patient data
- If tools return no data, clearly state "No data found"
- Always base responses on actual tool results

TOOL USAGE STRATEGY:
- For comprehensive medical history: Use multiple tools (patient details, conditions, medications, observations, allergies)
- For specific queries: Use the most relevant tool
- Always call tools with just the patient ID (no extra text)

RESPONSE FORMAT:
- Start with what you found in the EMR system
- Provide clear, organized information
- Include clinical recommendations when appropriate
- Always end with guidance for next steps

You have access to tools that can retrieve real patient data. Use them wisely and systematically."""
    
    def create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with function calling"""
        
        # Create function calling prompt - much more robust
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("human", "{input}"),
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