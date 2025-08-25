"""
LangChain-based chat service with strict tool enforcement and anti-hallucination measures
"""
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from langchain.agents import AgentExecutor, create_react_agent
# Memory deprecated - using chat_history directly instead
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.tools import Tool, StructuredTool
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.runnable import RunnablePassthrough
from pydantic import BaseModel, Field

from app.config import settings
from app.services.session_service import SessionService
from app.models import SessionData
from http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)

class MedicalQueryClassifier(BaseModel):
    """Classifies if a query requires medical data retrieval"""
    requires_tools: bool = Field(description="True if query needs patient data from EMR")
    tool_needed: Optional[str] = Field(description="Which tool to use if any")
    reason: str = Field(description="Brief explanation of decision")

class LangChainChatService:
    """Enhanced chat service using LangChain with strict tool enforcement"""
    
    def __init__(self, mcp_client: HTTPMCPClient, session_service: SessionService):
        self.mcp_client = mcp_client
        self.session_service = session_service
        
        # Initialize LangChain Groq LLM with valid Groq model
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model="moonshotai/kimi-k2-instruct",  # Valid Groq model with tool support
            temperature=0,  # Deterministic for medical data
            max_retries=3,
        )
        
        # Create tools with structured definitions
        self.tools = self._create_langchain_tools()
        
        # Enhanced anti-hallucination system prompt for ReAct agent
        self.system_prompt = """You are an EMR (Electronic Medical Records) assistant with STRICT rules:

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

        # Create agent with forced tool usage
        self.agent_executor = self._create_agent_executor()
        
    def _create_langchain_tools(self) -> List[Tool]:
        """Create LangChain tools from MCP client"""
        
        tools = []
        
        # Search patients tool
        def search_patients_wrapper(query: str) -> str:
            """Search for patients - REQUIRED for finding patients"""
            try:
                import asyncio
                # Parse query to extract search parameters
                params = {}
                if "name:" in query:
                    params["name"] = query.split("name:")[1].split(",")[0].strip()
                if "id:" in query:
                    params["mrn"] = query.split("id:")[1].split(",")[0].strip()
                    
                result = asyncio.run(self.mcp_client.execute_tool("search_patients", params))
                return json.dumps(result) if result else "No patients found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error searching patients: {str(e)}"
        
        tools.append(Tool(
            name="search_patients",
            func=search_patients_wrapper,
            description="Search for patients by name or ID. Use format: 'name:John Doe' or 'id:12345'"
        ))
        
        # Get patient details tool
        def get_patient_details_wrapper(patient_id: str) -> str:
            """Get patient demographics - REQUIRED for patient info queries"""
            try:
                import asyncio
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_details", {"patientId": patient_id}))
                return json.dumps(result) if result else "No patient details found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving patient details: {str(e)}"
        
        tools.append(Tool(
            name="get_patient_details",
            func=get_patient_details_wrapper,
            description="Get comprehensive patient information. MUST USE for any patient info query."
        ))
        
        # Get patient conditions tool
        def get_conditions_wrapper(patient_id: str) -> str:
            """Get patient conditions - REQUIRED for diagnosis queries"""
            try:
                import asyncio
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_conditions", {"patientId": patient_id}))
                return json.dumps(result) if result else "No conditions found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving conditions: {str(e)}"
        
        tools.append(Tool(
            name="get_patient_conditions",
            func=get_conditions_wrapper,
            description="Get all medical conditions/diagnoses. MUST USE for diagnosis queries."
        ))
        
        # Get patient medications tool
        def get_medications_wrapper(patient_id: str) -> str:
            """Get patient medications - REQUIRED for medication queries"""
            try:
                import asyncio
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_medications", {"patientId": patient_id}))
                return json.dumps(result) if result else "No medications found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving medications: {str(e)}"
        
        tools.append(Tool(
            name="get_patient_medications",
            func=get_medications_wrapper,
            description="Get all medications/prescriptions. MUST USE for medication queries."
        ))
        
        # Get patient observations tool
        def get_observations_wrapper(patient_id: str) -> str:
            """Get patient observations - REQUIRED for vitals/lab queries"""
            try:
                import asyncio
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_observations", {"patientId": patient_id}))
                return json.dumps(result) if result else "No observations found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving observations: {str(e)}"
        
        tools.append(Tool(
            name="get_patient_observations",
            func=get_observations_wrapper,
            description="Get vital signs, lab results, observations. MUST USE for vitals/labs queries."
        ))
        
        # Get patient allergies tool
        def get_allergies_wrapper(patient_id: str) -> str:
            """Get patient allergies - REQUIRED for allergy queries"""
            try:
                import asyncio
                result = asyncio.run(self.mcp_client.execute_tool("get_patient_allergies", {"patientId": patient_id}))
                return json.dumps(result) if result else "No allergies found"
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return f"Error retrieving allergies: {str(e)}"
        
        tools.append(Tool(
            name="get_patient_allergies", 
            func=get_allergies_wrapper,
            description="Get allergy information. MUST USE for allergy queries."
        ))
        
        return tools
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent with strict tool enforcement"""
        
        # Create custom ReAct prompt template
        from langchain.prompts import PromptTemplate
        
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
    
    async def _should_use_tools(self, message: str, patient_id: Optional[str]) -> MedicalQueryClassifier:
        """Classify if query needs tool usage"""
        
        classifier_prompt = """Analyze this query and determine if it requires retrieving medical data.
        
Query: {query}
Patient ID Available: {has_patient}

Medical keywords that REQUIRE tools:
- Patient info, demographics, details
- Diagnoses, conditions, problems
- Medications, prescriptions, drugs
- Vitals, observations, lab results
- Allergies, intolerances
- Discharge, summary, report

Output your analysis:"""
        
        parser = PydanticOutputParser(pydantic_object=MedicalQueryClassifier)
        
        prompt = ChatPromptTemplate.from_template(
            classifier_prompt + "\n{format_instructions}"
        )
        
        chain = prompt | self.llm | parser
        
        try:
            result = await chain.ainvoke({
                "query": message,
                "has_patient": "Yes" if patient_id else "No",
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except:
            # Default to requiring tools for safety
            return MedicalQueryClassifier(
                requires_tools=True,
                tool_needed="unknown",
                reason="Classification failed - defaulting to tool usage for safety"
            )
    
    async def process_chat(self, message: str, patient_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Process chat with strict tool enforcement"""
        
        logger.info(f"LangChain processing: message='{message}', patient_id='{patient_id}'")
        
        # Get patient session
        current_patient_id, session = await self.session_service.get_patient_session(patient_id)
        
        # Classify query
        classification = await self._should_use_tools(message, current_patient_id)
        logger.info(f"Query classification: {classification}")
        
        # Build context with patient ID
        context = f"Patient ID {current_patient_id} is selected" if current_patient_id else "No patient selected"
        full_message = f"{context}. {message}" if current_patient_id else message
        
        # Prepare chat history from session (using new approach without deprecated memory)
        from langchain_core.messages import HumanMessage, AIMessage
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
            # Non-medical query - safe to respond without tools
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt.replace("{tools}", "N/A").replace("{tool_names}", "None")),
                HumanMessage(content=message)
            ])
            response = response.content
        
        # Update session history
        if current_patient_id:
            await self.session_service.add_to_history(current_patient_id, message, response)
        
        return response, current_patient_id
    
    async def validate_no_hallucination(self, response: str) -> bool:
        """Post-process validation to catch any hallucinated medical data"""
        
        # Keywords that indicate potential hallucination
        medical_data_patterns = [
            r'\d+/\d+',  # Blood pressure
            r'\d+\s*mg',  # Medication dosage
            r'\d+\s*bpm',  # Heart rate
            r'allergic to \w+',  # Specific allergies
            r'diagnosed with \w+',  # Specific diagnoses
        ]
        
        # Check if response contains medical data without tool usage in recent steps
        import re
        for pattern in medical_data_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                logger.warning(f"Potential hallucination detected: {pattern}")
                return False
        
        return True