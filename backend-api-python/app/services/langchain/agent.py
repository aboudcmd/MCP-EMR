"""
LangChain agent module for EMR system
"""
import logging
from typing import List

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


class EMRAgentFactory:
    """Factory for creating EMR-specific LangChain agents"""
    
    def __init__(self, llm: ChatGroq, tools: List[Tool]):
        self.llm = llm
        self.tools = tools
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the EMR agent"""
        return """You are an EMR assistant. For medical information, you MUST use the available tools. Never make up medical data.

IMPORTANT: You must follow this EXACT format:

Question: the input question
Thought: what I need to do
Action: tool_name
Action Input: tool_input
Observation: tool_result
Thought: what I learned
Final Answer: my response

TOOLS AVAILABLE: {tool_names}

For complete medical history queries, use MULTIPLE tools:
1. get_patient_details (for demographics)  
2. get_patient_conditions (for diagnoses)
3. get_patient_medications (for prescriptions)
4. get_patient_observations (for vitals/labs)
5. get_patient_allergies (for allergies)

EXAMPLE:

Question: Show me complete medical history for patient 123
Thought: I need to get comprehensive medical information for patient 123
Action: get_patient_details
Action Input: 123
Observation: {{patient details}}
Thought: Now I need conditions
Action: get_patient_conditions  
Action Input: 123
Observation: {{conditions}}
Thought: Now I need medications
Action: get_patient_medications
Action Input: 123
Observation: {{medications}}
Thought: I have enough information
Final Answer: Based on the EMR data: {{summary}}

Question: {input}
Thought:{agent_scratchpad}"""
    
    def create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with strict tool enforcement"""
        
        # Create custom ReAct prompt template
        prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template=self.system_prompt
        )
        
        # Create ReAct agent using the correct method for non-OpenAI models
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )
        
        # Create executor with better error handling
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # For debugging
            return_intermediate_steps=True,
            max_iterations=6,  # Reduce iterations to avoid infinite loops
            handle_parsing_errors="Check your output and make sure it conforms to the format instructions!",
            max_execution_time=60,  # Add timeout
        )
        
        return executor