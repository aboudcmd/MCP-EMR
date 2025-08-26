"""
Medical query classification module for LangChain service
"""
import logging
from typing import Optional

from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MedicalQueryClassifier(BaseModel):
    """Classifies if a query requires medical data retrieval"""
    requires_tools: bool = Field(description="True if query needs patient data from EMR")
    tool_needed: Optional[str] = Field(description="Which tool to use if any")
    reason: str = Field(description="Brief explanation of decision")


class QueryClassificationService:
    """Service for classifying medical queries to determine if tools are needed"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.classifier_prompt = """Analyze this query and determine if it requires retrieving medical data.
        
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
    
    async def should_use_tools(self, message: str, patient_id: Optional[str]) -> MedicalQueryClassifier:
        """Classify if query needs tool usage"""
        
        parser = PydanticOutputParser(pydantic_object=MedicalQueryClassifier)
        
        prompt = ChatPromptTemplate.from_template(
            self.classifier_prompt + "\n{format_instructions}"
        )
        
        chain = prompt | self.llm | parser
        
        try:
            result = await chain.ainvoke({
                "query": message,
                "has_patient": "Yes" if patient_id else "No",
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logger.warning(f"Classification failed: {e}")
            # Default to requiring tools for safety
            return MedicalQueryClassifier(
                requires_tools=True,
                tool_needed="unknown",
                reason="Classification failed - defaulting to tool usage for safety"
            )