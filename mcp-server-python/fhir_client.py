import httpx
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

from types_models import (
    SearchPatientsArgs,
    GetPatientObservationsArgs,
    GetPatientEncountersArgs
)

class FHIRClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/fhir+json",
        }
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
    
    async def _make_request(self, method: str, path: str, params: Optional[Dict] = None):
        """Make HTTP request to FHIR server"""
        async with httpx.AsyncClient() as client:
            # Ensure path starts with /fhir for Spark FHIR server
            if not path.startswith('/fhir'):
                path = f"/fhir{path}"
            url = f"{self.base_url.rstrip('/')}{path}"
            if params:
                url = f"{url}?{urlencode(params)}"
            
            response = await client.request(method, url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def search_patients(self, args: SearchPatientsArgs):
        """Search for patients in Spark FHIR server"""
        params = {}
        if args.name:
            params["name"] = args.name
        if args.mrn:
            params["identifier"] = f"http://nphies.sa/identifier/mrn|{args.mrn}"
        if args.nationalId:
            params["identifier"] = f"http://nphies.sa/identifier/nationalid|{args.nationalId}"
        if args.iqama:
            params["identifier"] = f"http://nphies.sa/identifier/iqama|{args.iqama}"
        if args.birthDate:
            params["birthdate"] = args.birthDate
        if args.gender:
            params["gender"] = args.gender
        if args.phone:
            params["telecom"] = f"phone|{args.phone}"
        if args.email:
            params["telecom"] = f"email|{args.email}"
        
        data = await self._make_request("GET", "/Patient", params)
        return self._format_bundle(data)
    
    async def get_patient_details(self, patient_id: str):
        """Get detailed patient information"""
        data = await self._make_request("GET", f"/Patient/{patient_id}")
        return self._format_patient(data)
    
    async def get_patient_conditions(self, patient_id: str, clinical_status: Optional[str] = None):
        """Get patient conditions/diagnoses"""
        params = {"patient": patient_id}
        if clinical_status:
            params["clinical-status"] = clinical_status
        
        data = await self._make_request("GET", "/Condition", params)
        return self._format_conditions(data)
    
    async def get_patient_medications(self, patient_id: str, status: Optional[str] = None):
        """Get patient medications"""
        params = {"patient": patient_id}
        if status:
            params["status"] = status
        
        data = await self._make_request("GET", "/MedicationRequest", params)
        return self._format_medications(data)
    
    async def get_patient_observations(self, args: GetPatientObservationsArgs):
        """Get patient observations (vitals, lab results)"""
        params = {"patient": args.patientId}
        if args.category:
            params["category"] = args.category
        if args.code:
            params["code"] = args.code
        
        # Handle date range
        if args.dateFrom or args.dateTo:
            date_range = []
            if args.dateFrom:
                date_range.append(f"ge{args.dateFrom}")
            if args.dateTo:
                date_range.append(f"le{args.dateTo}")
            params["date"] = ",".join(date_range)
        
        data = await self._make_request("GET", "/Observation", params)
        return self._format_observations(data)
    
    async def get_patient_encounters(self, args: GetPatientEncountersArgs):
        """Get patient encounters/visits"""
        params = {"patient": args.patientId}
        if args.type:
            params["type"] = args.type
        
        # Handle date range
        if args.dateFrom or args.dateTo:
            date_range = []
            if args.dateFrom:
                date_range.append(f"ge{args.dateFrom}")
            if args.dateTo:
                date_range.append(f"le{args.dateTo}")
            params["date"] = ",".join(date_range)
        
        data = await self._make_request("GET", "/Encounter", params)
        return self._format_encounters(data)
    
    async def get_patient_allergies(self, patient_id: str):
        """Get patient allergies"""
        params = {"patient": patient_id}
        data = await self._make_request("GET", "/AllergyIntolerance", params)
        return self._format_allergies(data)
    
    # Formatting methods
    def _format_bundle(self, bundle: Dict) -> Dict:
        """Format FHIR bundle response"""
        if not bundle.get("entry"):
            return {"total": 0, "results": []}
        
        return {
            "total": bundle.get("total", 0),
            "results": [self._format_patient(entry["resource"]) for entry in bundle["entry"]]
        }
    
    def _format_patient(self, patient: Dict) -> Dict:
        """Format patient resource for Spark FHIR server"""
        name_parts = []
        if patient.get("name") and len(patient["name"]) > 0:
            name = patient["name"][0]
            # Use text field first if available, otherwise construct from given/family
            if name.get("text"):
                formatted_name = name["text"]
            else:
                if name.get("given"):
                    name_parts.extend(name["given"])
                if name.get("family"):
                    name_parts.append(name["family"])
                formatted_name = " ".join(name_parts) if name_parts else "Unknown"
        else:
            formatted_name = "Unknown"
        
        # Extract phone and email
        phone = None
        email = None
        if patient.get("telecom"):
            phone_contact = next((t for t in patient["telecom"] if t.get("system") == "phone"), None)
            email_contact = next((t for t in patient["telecom"] if t.get("system") == "email"), None)
            if phone_contact:
                phone = phone_contact.get("value")
            if email_contact:
                email = email_contact.get("value")
        
        # Extract MRN and National ID
        mrn = None
        national_id = None
        iqama = None
        if patient.get("identifier"):
            for identifier in patient["identifier"]:
                system = identifier.get("system", "")
                if "mrn" in system:
                    mrn = identifier.get("value")
                elif "nationalid" in system:
                    national_id = identifier.get("value")
                elif "iqama" in system:
                    iqama = identifier.get("value")
        
        # Extract marital status
        marital_status = None
        if patient.get("maritalStatus") and patient["maritalStatus"].get("coding"):
            marital_status = patient["maritalStatus"]["coding"][0].get("display")
        
        # Extract citizenship
        citizenship = None
        if patient.get("extension"):
            citizenship_ext = next((ext for ext in patient["extension"] if "citizenship" in ext.get("url", "")), None)
            if citizenship_ext and citizenship_ext.get("extension"):
                code_ext = citizenship_ext["extension"][0]
                if code_ext.get("valueCodeableConcept") and code_ext["valueCodeableConcept"].get("coding"):
                    citizenship = code_ext["valueCodeableConcept"]["coding"][0].get("code")
        
        return {
            "id": patient.get("id"),
            "name": formatted_name,
            "birthDate": patient.get("birthDate"),
            "gender": patient.get("gender"),
            "mrn": mrn,
            "nationalId": national_id,
            "iqama": iqama,
            "phone": phone,
            "email": email,
            "active": patient.get("active"),
            "maritalStatus": marital_status,
            "citizenship": citizenship,
            "country": patient.get("address", [{}])[0].get("country") if patient.get("address") else None,
        }
    
    def _format_conditions(self, bundle: Dict) -> List[Dict]:
        """Format conditions bundle"""
        if not bundle.get("entry"):
            return []
        
        conditions = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            code_display = None
            if resource.get("code"):
                if resource["code"].get("coding") and len(resource["code"]["coding"]) > 0:
                    code_display = resource["code"]["coding"][0].get("display")
                elif resource["code"].get("text"):
                    code_display = resource["code"]["text"]
            
            clinical_status = None
            if resource.get("clinicalStatus") and resource["clinicalStatus"].get("coding"):
                clinical_status = resource["clinicalStatus"]["coding"][0].get("code")
            
            conditions.append({
                "id": resource.get("id"),
                "code": code_display,
                "clinicalStatus": clinical_status,
                "onsetDateTime": resource.get("onsetDateTime"),
                "recordedDate": resource.get("recordedDate"),
            })
        
        return conditions
    
    def _format_medications(self, bundle: Dict) -> List[Dict]:
        """Format medications bundle"""
        if not bundle.get("entry"):
            return []
        
        medications = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            med_text = None
            if resource.get("medicationCodeableConcept"):
                if resource["medicationCodeableConcept"].get("text"):
                    med_text = resource["medicationCodeableConcept"]["text"]
                elif resource["medicationCodeableConcept"].get("coding"):
                    med_text = resource["medicationCodeableConcept"]["coding"][0].get("display")
            
            dosage = None
            if resource.get("dosageInstruction") and len(resource["dosageInstruction"]) > 0:
                dosage = resource["dosageInstruction"][0].get("text")
            
            medications.append({
                "id": resource.get("id"),
                "medication": med_text,
                "status": resource.get("status"),
                "dosage": dosage,
                "authoredOn": resource.get("authoredOn"),
            })
        
        return medications
    
    def _format_observations(self, bundle: Dict) -> List[Dict]:
        """Format observations bundle"""
        if not bundle.get("entry"):
            return []
        
        observations = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            
            # Get observation type
            obs_type = None
            if resource.get("code"):
                if resource["code"].get("coding") and len(resource["code"]["coding"]) > 0:
                    obs_type = resource["code"]["coding"][0].get("display")
                elif resource["code"].get("text"):
                    obs_type = resource["code"]["text"]
            
            # Get value
            value = None
            if resource.get("valueQuantity"):
                value = f"{resource['valueQuantity'].get('value')} {resource['valueQuantity'].get('unit', '')}"
            
            observations.append({
                "id": resource.get("id"),
                "type": obs_type,
                "value": value,
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "status": resource.get("status"),
            })
        
        return observations
    
    def _format_encounters(self, bundle: Dict) -> List[Dict]:
        """Format encounters bundle"""
        if not bundle.get("entry"):
            return []
        
        encounters = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            
            # Get encounter type
            enc_type = None
            if resource.get("type") and len(resource["type"]) > 0:
                enc_type = resource["type"][0].get("text")
            
            encounters.append({
                "id": resource.get("id"),
                "type": enc_type,
                "status": resource.get("status"),
                "period": resource.get("period"),
                "serviceProvider": resource.get("serviceProvider", {}).get("display"),
            })
        
        return encounters
    
    def _format_allergies(self, bundle: Dict) -> List[Dict]:
        """Format allergies bundle"""
        if not bundle.get("entry"):
            return []
        
        allergies = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            
            # Get substance
            substance = None
            if resource.get("code"):
                if resource["code"].get("coding") and len(resource["code"]["coding"]) > 0:
                    substance = resource["code"]["coding"][0].get("display")
                elif resource["code"].get("text"):
                    substance = resource["code"]["text"]
            
            allergies.append({
                "id": resource.get("id"),
                "substance": substance,
                "criticality": resource.get("criticality"),
                "type": resource.get("type"),
                "recordedDate": resource.get("recordedDate"),
            })
        
        return allergies