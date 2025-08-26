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
        return """You are an EMR (Electronic Medical Records) assistant with STRICT rules:

CRITICAL SAFETY REQUIREMENTS:
1. You MUST use tools for ALL medical information - NO EXCEPTIONS
2. NEVER make up patient data, even if it seems reasonable
3. If a tool returns empty/error, say "No data found" - do not improvise
4. Every medical fact must come from a tool response

QUERY HANDLING PROTOCOL:
- Patient info query → MUST use get_patient_details tool
- Conditions/diagnoses → MUST use get_patient_conditions tool  
- Medications → MUST use get_patient_medications tool
- Vital signs/labs → MUST use get_patient_observations tool
- Allergies → MUST use get_patient_allergies tool
- Patient search → MUST use search_patients tool

RESPONSE RULES:
- Tool returns data → Report ONLY what was returned
- Tool returns empty → Say "No [type] records found for this patient"
- Tool fails → Say "Unable to retrieve [type] data at this time"
- No patient ID → Say "Please provide a patient ID first"

ABSOLUTELY FORBIDDEN:
- Inventing patient names, IDs, or demographics
- Creating plausible-sounding medical data
- Filling gaps with generic medical information
- Assuming allergies, conditions, or medications

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

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
        
        # Create executor with strict settings
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # For debugging
            return_intermediate_steps=True,
            max_iterations=10,  # Allow more iterations for complex reasoning
            handle_parsing_errors=True,
        )
        
        return executor