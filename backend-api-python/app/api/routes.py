"""
API routes for EMR Backend
"""
import logging
import os, httpx
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dateutil.parser import isoparse

from app.models import ChatRequest, ChatResponse, SessionClearResponse, HealthResponse
from app.services.langchain_chat_service import LangChainChatService
from app.services.session_service import SessionService
from app.dependencies import get_chat_service, get_session_service
from app.config import settings
from dotenv import load_dotenv

load_dotenv()

FHIR_BASE = os.getenv("FHIR_SERVER_URL")
FHIR_USER = os.getenv("FHIR_USERNAME")    
FHIR_PASS = os.getenv("FHIR_PASSWORD")   

LOINC = {"height":"8302-2","weight":"29463-7","bp":"85354-9","sys":"8480-6","dia":"8462-4"}

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.API_VERSION
    )

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: LangChainChatService = Depends(get_chat_service)
):
    """Handle chat requests with patient-scoped sessions"""
    try:
        logger.info(f"Chat request: message='{request.message}', patient_id='{request.patientId}'")
        
        response_content, patient_id = await chat_service.process_chat(
            message=request.message,
            patient_id=request.patientId
        )
        
        logger.info("Chat response generated successfully")
        
        return ChatResponse(
            response=response_content,
            patientId=patient_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/patient/{patient_id}/session", response_model=SessionClearResponse)
async def clear_patient_session(
    patient_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Clear conversation history for a specific patient"""
    try:
        success = await session_service.clear_patient_session(patient_id)
        
        if success:
            logger.info(f"Session for patient {patient_id} cleared")
            return SessionClearResponse(
                status="patient session cleared",
                patientId=patient_id
            )
        else:
            return SessionClearResponse(
                status="patient session not found",
                patientId=patient_id
            )
            
    except Exception as e:
        logger.error(f"Error clearing session for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def eff_dt(o: dict):
    return o.get("effectiveDateTime") or o.get("issued")

@router.get("/api/patients/{patient_id}/vitals/latest")
async def latest_vitals(patient_id: str):
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    params = {
        "patient": patient_id,
        "code": f"{LOINC['height']},{LOINC['weight']},{LOINC['bp']}",
        "_sort": "-date",
        "_count": "80",
        "_elements": "id,code,effectiveDateTime,issued,valueQuantity,component"
    }

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(f"{FHIR_BASE}fhir/Observation",
                                 params=params,
                                 headers={"Accept":"application/fhir+json"})
    except httpx.RequestError as e:
        raise HTTPException(502, f"FHIR unreachable: {e}") from e

    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    bundle = r.json()
    entries = [e["resource"] for e in bundle.get("entry", []) if e.get("resource")]

    # Sort client-side as a fallback if server ignores _sort
    entries.sort(key=lambda o: isoparse(eff_dt(o) or "1900-01-01T00:00:00Z"), reverse=True)

    latest = {"height": None, "weight": None, "bp": None}
    for o in entries:
        code = ((o.get("code") or {}).get("coding") or [{}])[0].get("code")
        if code == LOINC["height"] and not latest["height"]: latest["height"] = o
        elif code == LOINC["weight"] and not latest["weight"]: latest["weight"] = o
        elif code == LOINC["bp"] and not latest["bp"]: latest["bp"] = o
        if all(latest.values()): break

    if not any(latest.values()):
        raise HTTPException(404, "No vitals found")

    def q(o):
        if not o: return None, None, None, None
        qv = o.get("valueQuantity") or {}
        return qv.get("value"), qv.get("unit"), eff_dt(o), o.get("id")

    h_val,h_unit,h_time,h_id = q(latest["height"])
    w_val,w_unit,w_time,w_id = q(latest["weight"])

    sys_val=dia_val=None
    unit_bp="mmHg"
    bp_time=bp_id=None
    if latest["bp"]:
        bp_time = eff_dt(latest["bp"])
        bp_id   = latest["bp"].get("id")
        for c in latest["bp"].get("component", []):
            ccode = ((c.get("code") or {}).get("coding") or [{}])[0].get("code")
            if ccode == LOINC["sys"]:
                sys_val = (c.get("valueQuantity") or {}).get("value")
                unit_bp = (c.get("valueQuantity") or {}).get("unit") or unit_bp
            elif ccode == LOINC["dia"]:
                dia_val = (c.get("valueQuantity") or {}).get("value")
                unit_bp = (c.get("valueQuantity") or {}).get("unit") or unit_bp

    return {
        "patient": patient_id,
        "height": None if h_val is None else {"value": h_val, "unit": h_unit, "effective": h_time, "observationId": h_id},
        "weight": None if w_val is None else {"value": w_val, "unit": w_unit, "effective": w_time, "observationId": w_id},
        "bloodPressure": None if not bp_time else {
            "systolic": sys_val, "diastolic": dia_val, "unit": unit_bp,
            "effective": bp_time, "observationId": bp_id
        }
    }

@router.get("/api/patients")
async def get_all_patients():
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    params = {
        "_elements": "id",
        "_count": "1000000000"
    }

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(f"{FHIR_BASE}fhir/Patient",
                                 params=params,
                                 headers={"Accept":"application/fhir+json"})
    except httpx.RequestError as e:
        raise HTTPException(502, f"FHIR unreachable: {e}") from e

    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    bundle = r.json()
    patients = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("id"):
            patients.append({"id": resource["id"]})

    return {"patients": patients, "total": len(patients)}

@router.get("/api/patients/{patient_id}")
async def get_patient_demographics(patient_id: str):
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(f"{FHIR_BASE}fhir/Patient/{patient_id}",
                                 headers={"Accept":"application/fhir+json"})
    except httpx.RequestError as e:
        raise HTTPException(502, f"FHIR unreachable: {e}") from e

    if r.status_code == 404:
        raise HTTPException(404, "Patient not found")
    elif r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    patient = r.json()
    return patient
