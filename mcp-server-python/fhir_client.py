import httpx
import logging
import base64
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

from types_models import (
    SearchPatientsArgs,
    GetPatientObservationsArgs,
    GetPatientEncountersArgs,
    GetPatientDiagnosticReportsArgs
)

logger = logging.getLogger(__name__)

# ⚙️ FHIR RESOURCE LIMITS - Control how many items are retrieved for each resource type
# Increase these numbers if you need more results, but be aware of performance impact
FHIR_LIMITS = {
    "conditions": 100,      # Medical conditions/diagnoses
    "medications": 100,     # Medications and prescriptions
    "observations": 200,    # Vitals, labs, imaging (increased from 100)
    "encounters": 100,      # Visits and encounters
    "allergies": 100,       # Allergy intolerances
    "diagnostic_reports": 100  # Diagnostic reports (if used)
}

class FHIRClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/fhir+json",
        }

        # Support both Bearer token and Basic auth
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        elif username and password:
            # Basic authentication
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
            logger.info(f"Using basic authentication for user: {username}")
    
    async def _make_request(self, method: str, path: str, params: Optional[Dict] = None, form_data: Optional[Dict] = None):
        """Make HTTP request to FHIR server with enhanced error handling"""
        async with httpx.AsyncClient() as client:
            # Ensure path starts with /fhir for Spark FHIR server
            if not path.startswith('/fhir'):
                path = f"/fhir{path}"
            url = f"{self.base_url.rstrip('/')}{path}"

            # Prepare headers
            headers = self.headers.copy()

            logger.info("="*40)
            logger.info(f"FHIR CLIENT: Making request to FHIR server")
            logger.info(f"Method: {method}")
            logger.info(f"URL: {url}")

            try:
                if form_data:
                    # POST request with form data
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                    logger.info(f"Form data: {form_data}")
                    response = await client.request(method, url, data=form_data, headers=headers)
                else:
                    # GET request with query parameters
                    if params:
                        url = f"{url}?{urlencode(params)}"
                        logger.info(f"Query params: {params}")
                    logger.info(f"Full URL: {url}")
                    response = await client.request(method, url, headers=headers)

                logger.info(f"✅ FHIR response status: {response.status_code}")

                response.raise_for_status()
                result = response.json()

            except httpx.HTTPStatusError as e:
                # Enhanced error handling for HTTP errors
                status_code = e.response.status_code
                logger.error(f"FHIR server error: {status_code} - {e.response.text[:200]}")

                # Parse error details from FHIR OperationOutcome if available
                error_detail = "Unknown error"
                try:
                    error_response = e.response.json()
                    if error_response.get("resourceType") == "OperationOutcome":
                        issues = error_response.get("issue", [])
                        if issues:
                            error_detail = issues[0].get("diagnostics", issues[0].get("details", {}).get("text", error_detail))
                except:
                    error_detail = e.response.text[:200] if e.response.text else str(e)

                # User-friendly error messages based on status code
                if status_code == 400:
                    raise ValueError(f"Invalid request parameters. {error_detail}")
                elif status_code == 401:
                    raise PermissionError("Authentication failed. Please check credentials.")
                elif status_code == 403:
                    raise PermissionError("Access denied. You don't have permission to access this resource.")
                elif status_code == 404:
                    raise FileNotFoundError(f"Resource not found: {path}")
                elif status_code == 500:
                    raise RuntimeError("FHIR server error. Please try again or contact support.")
                elif status_code == 503:
                    raise RuntimeError("FHIR server is temporarily unavailable. Please try again later.")
                else:
                    raise RuntimeError(f"FHIR server error ({status_code}): {error_detail}")

            except httpx.TimeoutException:
                logger.error(f"FHIR request timeout for {url}")
                raise TimeoutError("Request timed out. The FHIR server is taking too long to respond.")

            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to FHIR server: {e}")
                raise ConnectionError("Cannot connect to FHIR server. Please check if the server is running.")

            except Exception as e:
                logger.error(f"Unexpected error in FHIR request: {e}", exc_info=True)
                raise RuntimeError(f"Unexpected error communicating with FHIR server: {str(e)}")
            
            # Log result summary
            if isinstance(result, dict):
                total = result.get('total', 'unknown')
                entry_count = len(result.get('entry', []))
                logger.info(f"FHIR response summary: total={total}, entries={entry_count}")
                if 'resourceType' in result:
                    logger.info(f"Resource type: {result['resourceType']}")
            elif isinstance(result, list):
                logger.info(f"FHIR response: list with {len(result)} items")
            else:
                logger.info(f"FHIR response type: {type(result)}")
            logger.info("="*40)
            
            return result
    
    async def search_patients(self, args: SearchPatientsArgs):
        """Search for patients in Spark FHIR server using POST _search endpoint"""
        form_data = {
            "_count": "50"  # Limit patient search results
        }
        if args.name:
            form_data["name"] = args.name
        if args.mrn:
            form_data["identifier"] = f"http://nphies.sa/identifier/mrn|{args.mrn}"
        if args.nationalId:
            form_data["identifier"] = f"http://nphies.sa/identifier/nationalid|{args.nationalId}"
        if args.iqama:
            form_data["identifier"] = f"http://nphies.sa/identifier/iqama|{args.iqama}"
        if args.birthDate:
            form_data["birthdate"] = args.birthDate
        if args.gender:
            form_data["gender"] = args.gender
        if args.phone:
            form_data["telecom"] = f"phone|{args.phone}"
        if args.email:
            form_data["telecom"] = f"email|{args.email}"
        
        data = await self._make_request("POST", "/Patient/_search", form_data=form_data)
        return self._format_bundle(data)
    
    async def get_patient_details(self, patient_id: str):
        """Get detailed patient information"""
        data = await self._make_request("GET", f"/Patient/{patient_id}")
        return self._format_patient(data)
    
    async def get_patient_everything(self, patient_id: str, resource_types: Optional[List[str]] = None):
        """Get all patient data using $everything endpoint"""
        # Build URL with multiple _type parameters as per Postman collection
        url = f"{self.base_url.rstrip('/')}/fhir/Patient/{patient_id}/$everything"
        
        if resource_types:
            # Add multiple _type query parameters
            type_params = "&".join([f"_type={rt}" for rt in resource_types])
            url = f"{url}?{type_params}"
        
        logger.info(f"Making FHIR $everything request: GET {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"FHIR $everything response: status={response.status_code}")
            if isinstance(data, dict):
                total = data.get('total', 'unknown')
                entry_count = len(data.get('entry', []))
                logger.info(f"$everything response: total={total}, entries={entry_count}")
            
            # Parse and format the comprehensive response
            return self._format_everything_response(data)
    
    async def get_patient_conditions(self, patient_id: str, clinical_status: Optional[str] = None):
        """Get patient conditions using Spark FHIR _search endpoint"""
        form_data = {
            "subject": patient_id,
            "_count": str(FHIR_LIMITS["conditions"])
        }
        if clinical_status:
            form_data["clinical-status"] = clinical_status
        
        data = await self._make_request("POST", "/Condition/_search", form_data=form_data)
        return self._format_conditions(data)
    
    async def get_patient_medications(self, patient_id: str, status: Optional[str] = None):
        """Get patient medications using Spark FHIR _search endpoint"""
        form_data = {
            "subject": patient_id,
            "_count": str(FHIR_LIMITS["medications"])
        }
        if status:
            form_data["status"] = status
        
        data = await self._make_request("POST", "/MedicationRequest/_search", form_data=form_data)
        return self._format_medications(data)
    
    async def get_patient_observations(self, args: GetPatientObservationsArgs):
        """Get patient observations using Spark FHIR _search endpoint"""
        form_data = {
            "subject": f"Patient/{args.patientId}",
            "_count": str(FHIR_LIMITS["observations"]),
            "_sort": "-date"  # Sort by date descending (most recent first)
        }
        if args.category:
            form_data["category"] = args.category
        if args.code:
            form_data["code"] = args.code
        
        # Handle date range
        if args.dateFrom or args.dateTo:
            date_range = []
            if args.dateFrom:
                date_range.append(f"ge{args.dateFrom}")
            if args.dateTo:
                date_range.append(f"le{args.dateTo}")
            form_data["date"] = ",".join(date_range)
        
        data = await self._make_request("POST", "/Observation/_search", form_data=form_data)
        formatted_result = self._format_observations(data)
        logger.info(f"Formatted {len(formatted_result.get('observations', []))} observations for patient {args.patientId}")
        
        return formatted_result
    
    async def get_patient_encounters(self, args: GetPatientEncountersArgs):
        """Get patient encounters/visits"""
        params = {
            "patient": args.patientId,
            "_count": str(FHIR_LIMITS["encounters"])
        }
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
        params = {
            "patient": patient_id,
            "_count": str(FHIR_LIMITS["allergies"])
        }
        data = await self._make_request("GET", "/AllergyIntolerance", params)
        return self._format_allergies(data)

    async def get_patient_diagnostic_reports(self, args: GetPatientDiagnosticReportsArgs):
        """Get patient diagnostic reports (lab results) using Spark FHIR _search endpoint"""
        form_data = {
            "subject": f"Patient/{args.patientId}",
            "_count": str(FHIR_LIMITS["diagnostic_reports"]),
            "_sort": "-date"  # Sort by date descending (most recent first)
        }
        if args.category:
            form_data["category"] = args.category
        if args.code:
            form_data["code"] = args.code

        # Handle date range
        if args.dateFrom or args.dateTo:
            date_range = []
            if args.dateFrom:
                date_range.append(f"ge{args.dateFrom}")
            if args.dateTo:
                date_range.append(f"le{args.dateTo}")
            form_data["date"] = ",".join(date_range)

        data = await self._make_request("POST", "/DiagnosticReport/_search", form_data=form_data)
        formatted_result = self._format_diagnostic_reports(data)
        logger.info(f"Formatted {len(formatted_result.get('diagnosticReports', []))} diagnostic reports for patient {args.patientId}")

        return formatted_result
    
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
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])
        
        logger.info(f"Conditions bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")
        
        if not entries:
            if total > 0:
                logger.warning(f"FHIR returned {total} conditions but no entries - likely pagination issue")
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
            
            # Handle onset - can be onsetDateTime or onsetString
            onset = resource.get("onsetDateTime") or resource.get("onsetString")
            
            conditions.append({
                "id": resource.get("id"),
                "code": code_display,
                "clinicalStatus": clinical_status,
                "onset": onset,
                "onsetDateTime": resource.get("onsetDateTime"),  # Keep for backward compatibility
                "recordedDate": resource.get("recordedDate"),
            })
        
        return conditions
    
    def _format_medications(self, bundle: Dict) -> Dict:
        """Format medications bundle"""
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])
        
        logger.info(f"Medications bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")
        
        if not entries:
            if total > 0:
                logger.warning(f"FHIR returned {total} medications but no entries - likely pagination issue")
            return {"total": total, "medications": []}
        
        medications = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            
            # Get medication name from different possible locations
            med_text = None
            med_code = None
            med_system = None
            
            # Check contained resources first (common in Saudi FHIR implementation)
            if resource.get("contained"):
                for contained in resource["contained"]:
                    if contained.get("resourceType") == "Medication" and contained.get("code"):
                        code = contained["code"]
                        if code.get("text"):
                            med_text = code["text"]
                        elif code.get("coding") and len(code["coding"]) > 0:
                            coding = code["coding"][0]
                            med_text = coding.get("display")
                            med_code = coding.get("code")
                            med_system = coding.get("system")
                        break
            
            # Fallback to medicationCodeableConcept (alternative structure)
            if not med_text and resource.get("medicationCodeableConcept"):
                med_concept = resource["medicationCodeableConcept"]
                if med_concept.get("text"):
                    med_text = med_concept["text"]
                elif med_concept.get("coding") and len(med_concept["coding"]) > 0:
                    coding = med_concept["coding"][0]
                    med_text = coding.get("display")
                    med_code = coding.get("code")
                    med_system = coding.get("system")
            
            # Fallback to medicationReference
            if not med_text and resource.get("medicationReference"):
                med_text = resource["medicationReference"].get("display", "Referenced Medication")
            
            # Get dosage information
            dosage = None
            dosage_details = []
            if resource.get("dosageInstruction") and len(resource["dosageInstruction"]) > 0:
                dosage_inst = resource["dosageInstruction"][0]
                dosage = dosage_inst.get("text")
                
                # Extract additional dosage details
                if dosage_inst.get("timing"):
                    timing = dosage_inst["timing"]
                    if timing.get("repeat"):
                        repeat = timing["repeat"]
                        frequency = repeat.get("frequency")
                        period = repeat.get("period")
                        period_unit = repeat.get("periodUnit")
                        if frequency and period:
                            dosage_details.append(f"Frequency: {frequency} times per {period} {period_unit}")
                
                if dosage_inst.get("route") and dosage_inst["route"].get("coding"):
                    route = dosage_inst["route"]["coding"][0].get("display", "")
                    if route:
                        dosage_details.append(f"Route: {route}")
                
                if dosage_inst.get("doseAndRate"):
                    dose_rate = dosage_inst["doseAndRate"][0]
                    if dose_rate.get("doseQuantity"):
                        dose_qty = dose_rate["doseQuantity"]
                        dose_value = dose_qty.get("value")
                        dose_unit = dose_qty.get("unit")
                        if dose_value and dose_unit:
                            dosage_details.append(f"Dose: {dose_value} {dose_unit}")
            
            # Get category/classification
            category = None
            if resource.get("category") and len(resource["category"]) > 0:
                if resource["category"][0].get("coding"):
                    category = resource["category"][0]["coding"][0].get("display")
            
            # Get priority
            priority = None
            if resource.get("priority"):
                priority = resource["priority"]
            
            # Get reason for medication
            reason = None
            if resource.get("reasonCode") and len(resource["reasonCode"]) > 0:
                if resource["reasonCode"][0].get("coding"):
                    reason = resource["reasonCode"][0]["coding"][0].get("display")
                elif resource["reasonCode"][0].get("text"):
                    reason = resource["reasonCode"][0]["text"]
            
            # Get prescriber information
            requester = None
            if resource.get("requester"):
                requester = resource["requester"].get("display")
            
            medications.append({
                "id": resource.get("id"),
                "medication": med_text or "Unknown Medication",
                "medicationCode": med_code,
                "medicationSystem": med_system,
                "status": resource.get("status"),
                "intent": resource.get("intent"),
                "category": category,
                "priority": priority,
                "dosage": dosage,
                "dosageDetails": dosage_details if dosage_details else None,
                "reason": reason,
                "requester": requester,
                "authoredOn": resource.get("authoredOn"),
                "dispenseRequest": resource.get("dispenseRequest"),
                "substitution": resource.get("substitution"),
                "note": resource.get("note")[0].get("text") if resource.get("note") else None
            })
        
        return {
            "total": bundle.get("total", len(medications)),
            "medications": medications
        }
    
    def _format_observations(self, bundle: Dict) -> Dict:
        """Format observations bundle"""
        # Log the bundle structure for debugging
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])
        
        logger.info(f"Observations bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")
        
        if not entries:
            # If no entries but total > 0, might be a pagination issue
            if total > 0:
                logger.warning(f"FHIR returned {total} observations but no entries - pagination issue?")
            return {"total": total, "observations": []}
        
        observations = []
        for entry in bundle["entry"]:
            resource = entry["resource"]
            
            # Get observation type/code
            obs_type = None
            obs_code = None
            obs_system = None
            if resource.get("code"):
                if resource["code"].get("coding") and len(resource["code"]["coding"]) > 0:
                    coding = resource["code"]["coding"][0]
                    obs_type = coding.get("display")
                    obs_code = coding.get("code")
                    obs_system = coding.get("system")
                elif resource["code"].get("text"):
                    obs_type = resource["code"]["text"]
            
            # Get category
            category = None
            if resource.get("category") and len(resource["category"]) > 0:
                if resource["category"][0].get("coding"):
                    category = resource["category"][0]["coding"][0].get("display")
            
            # Get value - handle valueQuantity, valueString, and component values
            value = None
            value_type = None
            components = []

            if resource.get("valueQuantity"):
                # Simple numeric value (labs, vitals)
                value_qty = resource["valueQuantity"]
                value = f"{value_qty.get('value')} {value_qty.get('unit', '')}"
                value_type = "quantity"
            elif resource.get("valueString"):
                # Text value (radiology reports, imaging results)
                value = resource["valueString"]
                value_type = "text"
            elif resource.get("component"):
                # Component values (e.g., systolic/diastolic blood pressure)
                value_type = "components"
                for component in resource["component"]:
                    comp_code = None
                    comp_value = None

                    if component.get("code") and component["code"].get("coding"):
                        comp_code = component["code"]["coding"][0].get("display")

                    if component.get("valueQuantity"):
                        comp_qty = component["valueQuantity"]
                        comp_value = f"{comp_qty.get('value')} {comp_qty.get('unit', '')}"

                    components.append({
                        "code": comp_code,
                        "value": comp_value
                    })

                # Create a combined value string for components
                if components:
                    comp_values = [f"{c['code']}: {c['value']}" for c in components if c['code'] and c['value']]
                    value = ", ".join(comp_values) if comp_values else None
            
            # Get interpretation
            interpretation = None
            if resource.get("interpretation") and len(resource["interpretation"]) > 0:
                if resource["interpretation"][0].get("coding"):
                    interpretation = resource["interpretation"][0]["coding"][0].get("display")
            
            # Get reference ranges
            reference_range = None
            if resource.get("referenceRange") and len(resource["referenceRange"]) > 0:
                ref_range = resource["referenceRange"][0]
                low = ref_range.get("low", {}).get("value")
                high = ref_range.get("high", {}).get("value")
                unit = ref_range.get("low", {}).get("unit") or ref_range.get("high", {}).get("unit")
                if low and high:
                    reference_range = f"{low}-{high} {unit}"
                elif low:
                    reference_range = f">{low} {unit}"
                elif high:
                    reference_range = f"<{high} {unit}"
            
            observations.append({
                "id": resource.get("id"),
                "code": obs_code,
                "codeSystem": obs_system,
                "type": obs_type,
                "category": category,
                "categoryCode": resource.get("category", [{}])[0].get("coding", [{}])[0].get("code") if resource.get("category") else None,
                "value": value,
                "valueType": value_type,
                "components": components if components else None,
                "interpretation": interpretation,
                "referenceRange": reference_range,
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "effectiveDate": resource.get("effectiveDate"),
                "status": resource.get("status"),
                "note": resource.get("note")[0].get("text") if resource.get("note") else None
            })
        
        # Sort observations by date (most recent first)
        try:
            observations.sort(
                key=lambda x: x.get('effectiveDateTime') or x.get('effectiveDate') or '1900-01-01',
                reverse=True
            )
            logger.info(f"Sorted {len(observations)} observations by date (most recent first)")
        except Exception as e:
            logger.warning(f"Could not sort observations by date: {e}")

        # Group observations by category for better organization
        vitals = [obs for obs in observations if obs.get('categoryCode') == 'vital-signs']
        labs = [obs for obs in observations if obs.get('categoryCode') == 'laboratory']
        imaging = [obs for obs in observations if obs.get('categoryCode') == 'imaging']
        other = [obs for obs in observations if obs.get('categoryCode') not in ['vital-signs', 'laboratory', 'imaging']]

        logger.info(f"Categorized observations: {len(vitals)} vitals, {len(labs)} labs, {len(imaging)} imaging, {len(other)} other")

        return {
            "total": bundle.get("total", len(observations)),
            "observations": observations,
            "vitals": vitals,
            "labs": labs,
            "imaging": imaging,
            "other": other
        }
    
    def _format_encounters(self, bundle: Dict) -> List[Dict]:
        """Format encounters bundle"""
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])
        
        logger.info(f"Encounters bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")
        
        if not entries:
            if total > 0:
                logger.warning(f"FHIR returned {total} encounters but no entries - likely pagination issue")
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
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])

        logger.info(f"Allergies bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")

        if not entries:
            if total > 0:
                logger.warning(f"FHIR returned {total} allergies but no entries - likely pagination issue")
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

    def _format_diagnostic_reports(self, bundle: Dict) -> Dict:
        """Format diagnostic reports bundle"""
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])

        logger.info(f"DiagnosticReports bundle: total={total}, has_entry={bool(entries)}, entry_count={len(entries)}")

        if not entries:
            if total > 0:
                logger.warning(f"FHIR returned {total} diagnostic reports but no entries - likely pagination issue")
            return {"total": total, "diagnosticReports": []}

        diagnostic_reports = []
        for entry in bundle["entry"]:
            resource = entry["resource"]

            # Get diagnostic report code/type
            code_display = None
            code_value = None
            code_system = None
            if resource.get("code"):
                if resource["code"].get("coding") and len(resource["code"]["coding"]) > 0:
                    coding = resource["code"]["coding"][0]
                    code_display = coding.get("display")
                    code_value = coding.get("code")
                    code_system = coding.get("system")
                elif resource["code"].get("text"):
                    code_display = resource["code"]["text"]

            # Get category
            category = None
            if resource.get("category") and len(resource["category"]) > 0:
                if resource["category"][0].get("coding"):
                    category = resource["category"][0]["coding"][0].get("display")

            # Get results references
            results = []
            if resource.get("result"):
                for result_ref in resource["result"]:
                    results.append(result_ref.get("reference"))

            diagnostic_reports.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "category": category,
                "code": code_display,
                "codeValue": code_value,
                "codeSystem": code_system,
                "subject": resource.get("subject", {}).get("reference"),
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "issued": resource.get("issued"),
                "results": results,
                "conclusion": resource.get("conclusion"),
                "conclusionCode": resource.get("conclusionCode"),
            })

        # Sort by effectiveDateTime (most recent first)
        try:
            diagnostic_reports.sort(
                key=lambda x: x.get('effectiveDateTime') or '1900-01-01',
                reverse=True
            )
            logger.info(f"Sorted {len(diagnostic_reports)} diagnostic reports by date (most recent first)")
        except Exception as e:
            logger.warning(f"Could not sort diagnostic reports by date: {e}")

        return {
            "total": bundle.get("total", len(diagnostic_reports)),
            "diagnosticReports": diagnostic_reports
        }
    
    def _format_everything_response(self, bundle: Dict) -> Dict:
        """Format $everything endpoint response with all patient data"""
        if not bundle.get("entry"):
            return {
                "patient": None,
                "observations": [],
                "conditions": [],
                "medications": [],
                "allergies": [],
                "encounters": []
            }
        
        # Separate resources by type
        patient_data = None
        observations = []
        conditions = []
        medications = []
        allergies = []
        encounters = []
        
        for entry in bundle["entry"]:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            if resource_type == "Patient":
                patient_data = self._format_patient(resource)
            elif resource_type == "Observation":
                observations.append(resource)
            elif resource_type == "Condition":
                conditions.append({"resource": resource})
            elif resource_type == "MedicationRequest":
                medications.append({"resource": resource})
            elif resource_type == "AllergyIntolerance":
                allergies.append({"resource": resource})
            elif resource_type == "Encounter":
                encounters.append({"resource": resource})
        
        # Format each resource type using existing formatters
        return {
            "patient": patient_data,
            "observations": self._format_observations({"entry": [{"resource": obs} for obs in observations]})["observations"],
            "conditions": self._format_conditions({"entry": conditions}),
            "medications": self._format_medications({"entry": medications})["medications"],
            "allergies": self._format_allergies({"entry": allergies}),
            "encounters": self._format_encounters({"entry": encounters}),
            "total_resources": len(bundle["entry"])
        }