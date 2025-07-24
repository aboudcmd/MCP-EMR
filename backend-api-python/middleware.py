# backend-api-python/middleware.py
class DataVerificationMiddleware:
    """Ensures responses contain only data from tool results"""
    
    def __init__(self):
        self.medical_terms = {
            'medications': ['albuterol', 'fluticasone', 'loratadine', 'insulin', 'metformin'],
            'conditions': ['asthma', 'diabetes', 'hypertension', 'scoliosis'],
            'vitals': ['blood pressure', 'temperature', 'heart rate', 'respiratory rate'],
        }
    
    def verify_response(self, response: str, tool_results: List[Dict]) -> bool:
        """Check if response contains only data from tool results"""
        response_lower = response.lower()
        
        # Extract all data points from tool results
        valid_data = []
        for result in tool_results:
            if isinstance(result, dict):
                valid_data.extend(self._extract_values(result))
        
        # Check for hallucinated medical data
        for category, terms in self.medical_terms.items():
            for term in terms:
                if term in response_lower and term not in str(valid_data).lower():
                    logger.warning(f"Potential hallucination detected: {term}")
                    return False
        
        return True
    
    def _extract_values(self, obj: Any, values: List = None) -> List:
        """Recursively extract all values from nested structures"""
        if values is None:
            values = []
        
        if isinstance(obj, dict):
            for v in obj.values():
                self._extract_values(v, values)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_values(item, values)
        else:
            values.append(str(obj))
        
        return values