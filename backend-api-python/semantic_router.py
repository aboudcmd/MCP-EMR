"""Semantic similarity-based query routing for tool selection"""
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

logger = logging.getLogger(__name__)

class SemanticQueryRouter:
    """Semantic similarity-based query routing system"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", similarity_threshold: float = 0.3):
        """
        Initialize semantic router
        
        Args:
            model_name: Sentence transformer model to use
            similarity_threshold: Minimum similarity score to consider a match
        """
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded semantic model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            self.model = None
        
        self.similarity_threshold = similarity_threshold
        
        # Tool descriptions and example queries for each tool
        self.tool_definitions = {
            "search_patients": {
                "description": "Search for patients using name, ID, demographics, or other identifiers",
                "examples": [
                    "find patient named John Smith",
                    "search for patients with MRN 123456", 
                    "look for patient with national ID 987654321",
                    "who is patient 416768",
                    "find patients named Mohammed",
                    "search patients by phone number"
                ],
                "keywords": ["search", "find", "locate", "patient", "patients", "name", "id", "mrn", "national"]
            },
            "get_patient_details": {
                "description": "Get detailed patient information including demographics and basic profile",
                "examples": [
                    "show patient details for ID 416768",
                    "get patient profile information",
                    "tell me about this patient",
                    "patient demographics and information",
                    "show me patient summary",
                    "display patient profile"
                ],
                "keywords": ["details", "profile", "information", "demographics", "about", "summary", "show"]
            },
            "get_patient_observations": {
                "description": "Get patient vital signs, measurements, lab results, and clinical observations",
                "examples": [
                    "what are the patient's vital signs",
                    "show patient observations and lab results",
                    "get blood pressure readings",
                    "patient weight and height measurements",
                    "vitals and clinical observations",
                    "lab test results and values",
                    "body measurements and vital signs",
                    "الضغط للمريض",
                    "العلامات الحيوية",
                    "قياس الضغط",
                    "نتائج المختبر",
                    "الوزن والطول",
                    "الفحوصات الطبية"
                ],
                "keywords": ["vitals", "observations", "measurements", "labs", "results", "blood pressure", "weight", "height", "readings", "ضغط", "علامات", "قياس", "فحوصات", "وزن", "طول"]
            },
            "get_patient_conditions": {
                "description": "Get patient medical conditions, diagnoses, and health problems",
                "examples": [
                    "what conditions does the patient have",
                    "patient medical diagnoses",
                    "health problems and conditions",
                    "what diseases is patient diagnosed with",
                    "medical conditions and illnesses",
                    "patient diagnosis history",
                    "والحالات؟",
                    "ما هي الحالات الطبية",
                    "التشخيص الطبي للمريض",
                    "الأمراض المشخصة",
                    "الحالة الصحية",
                    "تاريخ المرض"
                ],
                "keywords": ["conditions", "diagnoses", "diseases", "problems", "illness", "medical", "health", "حالات", "تشخيص", "أمراض", "صحية", "مرض"]
            },
            "get_patient_medications": {
                "description": "Get patient current medications, prescriptions, and drug therapy",
                "examples": [
                    "what medications is the patient taking",
                    "current prescriptions and drugs",
                    "patient medication list",
                    "prescribed medicines and pills",
                    "drug therapy and medications",
                    "pharmaceutical treatments",
                    "الأدوية الحالية",
                    "ما هي الأدوية",
                    "الوصفات الطبية",
                    "العلاج الدوائي",
                    "قائمة الأدوية",
                    "الأدوية المطلوبة"
                ],
                "keywords": ["medications", "prescriptions", "drugs", "medicines", "pills", "therapy", "treatment", "أدوية", "وصفات", "علاج", "دواء"]
            },
            "get_patient_allergies": {
                "description": "Get patient allergies, intolerances, and adverse reactions",
                "examples": [
                    "patient allergies and intolerances",
                    "what is the patient allergic to",
                    "drug allergies and reactions",
                    "food allergies and intolerances", 
                    "adverse reactions to medications",
                    "allergy information"
                ],
                "keywords": ["allergies", "allergic", "intolerances", "reactions", "adverse"]
            },
            "get_patient_encounters": {
                "description": "Get patient hospital visits, appointments, admissions, and healthcare encounters",
                "examples": [
                    "patient hospital visits and stays",
                    "appointment history and encounters",
                    "when was patient last seen",
                    "admission and discharge records",
                    "healthcare visits and appointments",
                    "encounter history"
                ],
                "keywords": ["visits", "appointments", "encounters", "admissions", "hospital", "seen", "stays"]
            }
        }
        
        # Pre-compute embeddings for tool descriptions and examples
        self._precompute_embeddings()
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for all tool descriptions and examples"""
        if not self.model:
            self.tool_embeddings = {}
            return
            
        self.tool_embeddings = {}
        
        for tool_name, config in self.tool_definitions.items():
            # Combine description with examples for better semantic representation
            text_samples = [config["description"]] + config["examples"]
            
            try:
                embeddings = self.model.encode(text_samples)
                # Use mean of all embeddings as tool representation
                tool_embedding = np.mean(embeddings, axis=0)
                self.tool_embeddings[tool_name] = tool_embedding
                
                logger.debug(f"Computed embedding for {tool_name}")
            except Exception as e:
                logger.error(f"Failed to compute embedding for {tool_name}: {e}")
                
        logger.info(f"Pre-computed embeddings for {len(self.tool_embeddings)} tools")
    
    def needs_tools(self, query: str) -> bool:
        """Determine if query needs any tools using semantic similarity"""
        if not self.model or not query.strip():
            return False
            
        # Quick heuristic checks first
        if self._is_clearly_conversational(query):
            return False
            
        if self._has_data_intent_signals(query):
            return True
        
        # Semantic similarity check
        best_tools = self.get_best_tools(query, top_k=1)
        return len(best_tools) > 0 and best_tools[0][1] > self.similarity_threshold
    
    def get_best_tools(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Get top-k most semantically similar tools for the query"""
        if not self.model or not self.tool_embeddings:
            return self._fallback_keyword_matching(query, top_k)
        
        try:
            # Encode the query
            query_embedding = self.model.encode([query.strip()])
            
            # Calculate similarities
            similarities = []
            for tool_name, tool_embedding in self.tool_embeddings.items():
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1), 
                    tool_embedding.reshape(1, -1)
                )[0][0]
                similarities.append((tool_name, similarity))
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter by threshold and return top-k
            filtered = [(tool, score) for tool, score in similarities if score > self.similarity_threshold]
            
            logger.info(f"Semantic similarity results for '{query[:50]}...': {filtered[:top_k]}")
            
            return filtered[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic similarity calculation: {e}")
            return self._fallback_keyword_matching(query, top_k)
    
    def _fallback_keyword_matching(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Fallback to keyword-based matching when semantic model fails"""
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        matches = []
        for tool_name, config in self.tool_definitions.items():
            keyword_overlap = len(query_words & set(config["keywords"]))
            if keyword_overlap > 0:
                # Normalize score by number of keywords
                score = keyword_overlap / len(config["keywords"])
                matches.append((tool_name, score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Keyword fallback results for '{query[:50]}...': {matches[:top_k]}")
        
        return matches[:top_k]
    
    def _is_clearly_conversational(self, query: str) -> bool:
        """Check if query is clearly conversational and doesn't need tools"""
        conversational_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon)\b',
            r'^(thank you|thanks|ok|okay|yes|no)\b',
            r'^(how are you|what\'s up|how\'s it going)\b',
            r'^(goodbye|bye|see you|talk to you later)\b',
        ]
        
        query_lower = query.lower().strip()
        for pattern in conversational_patterns:
            if re.match(pattern, query_lower):
                return True
        
        return False
    
    def _has_data_intent_signals(self, query: str) -> bool:
        """Check for strong data intent signals"""
        data_signals = [
            r'\b(what|how|when|where|which|who)\b',  # Question words
            r'\b(show|display|get|tell me|give me)\b',  # Request words
            r'\bpatient\s+\d+\b',  # Patient ID references
            r'\b(complete|full|medical)\s+(history|summary|record)\b',  # Comprehensive requests
        ]
        
        query_lower = query.lower()
        for pattern in data_signals:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def explain_routing(self, query: str) -> Dict[str, Any]:
        """Explain why certain tools were selected for debugging"""
        best_tools = self.get_best_tools(query, top_k=5)
        needs_tools = self.needs_tools(query)
        
        return {
            "query": query,
            "needs_tools": needs_tools,
            "best_tools": best_tools,
            "threshold": self.similarity_threshold,
            "conversational": self._is_clearly_conversational(query),
            "data_intent": self._has_data_intent_signals(query)
        }