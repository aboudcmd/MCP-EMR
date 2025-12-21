"""
Patient/FHIR Data API routes - Direct FHIR data endpoints
"""
import logging
import os
import httpx
from fastapi import APIRouter, HTTPException
from dateutil.parser import isoparse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Patients"])

FHIR_BASE = os.getenv("FHIR_SERVER_URL")
FHIR_USER = os.getenv("FHIR_USERNAME")
FHIR_PASS = os.getenv("FHIR_PASSWORD")

# LOINC codes for vital signs
LOINC = {
    "height": "8302-2",
    "weight": "29463-7",
    "bp": "85354-9",
    "sys": "8480-6",
    "dia": "8462-4"
}


def eff_dt(o: dict):
    """Extract effective datetime from observation"""
    return o.get("effectiveDateTime") or o.get("issued")


@router.get("/patients")
async def get_all_patients():
    """Get all patients (IDs only)"""
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    params = {
        "_elements": "id",
        "_count": "1000000000"
    }

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(
                f"{FHIR_BASE}fhir/Patient",
                params=params,
                headers={"Accept": "application/fhir+json"}
            )
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


@router.get("/patients/{patient_id}")
async def get_patient_demographics(patient_id: str):
    """Get patient demographics by ID"""
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(
                f"{FHIR_BASE}fhir/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"}
            )
    except httpx.RequestError as e:
        raise HTTPException(502, f"FHIR unreachable: {e}") from e

    if r.status_code == 404:
        raise HTTPException(404, "Patient not found")
    elif r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    patient = r.json()
    return patient


@router.get("/patients/{patient_id}/vitals/latest")
async def latest_vitals(patient_id: str):
    """Get latest vital signs for a patient"""
    if not (FHIR_USER and FHIR_PASS):
        raise HTTPException(500, "FHIR credentials not configured")

    params = {
        "patient": patient_id,
        "code": f"{LOINC['height']},{LOINC['weight']},{LOINC['bp']}",
        "_sort": "-date",
        "_count": "80",
        "_elements": "id,code,effectiveDateTime,issued,valueQuantity,component"
    }

    fhir_url = f"{FHIR_BASE}fhir/Observation"
    logger.info(f"FHIR REQUEST TO: {fhir_url}")

    try:
        async with httpx.AsyncClient(timeout=15, auth=(FHIR_USER, FHIR_PASS)) as client:
            r = await client.get(
                fhir_url,
                params=params,
                headers={"Accept": "application/fhir+json"}
            )
    except httpx.RequestError as e:
        logger.error(f"FHIR REQUEST FAILED: {fhir_url} - Error: {e}")
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
        if code == LOINC["height"] and not latest["height"]:
            latest["height"] = o
        elif code == LOINC["weight"] and not latest["weight"]:
            latest["weight"] = o
        elif code == LOINC["bp"] and not latest["bp"]:
            latest["bp"] = o
        if all(latest.values()):
            break

    if not any(latest.values()):
        raise HTTPException(404, "No vitals found")

    def q(o):
        if not o:
            return None, None, None, None
        qv = o.get("valueQuantity") or {}
        return qv.get("value"), qv.get("unit"), eff_dt(o), o.get("id")

    h_val, h_unit, h_time, h_id = q(latest["height"])
    w_val, w_unit, w_time, w_id = q(latest["weight"])

    sys_val = dia_val = None
    unit_bp = "mmHg"
    bp_time = bp_id = None
    if latest["bp"]:
        bp_time = eff_dt(latest["bp"])
        bp_id = latest["bp"].get("id")
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
        "height": None if h_val is None else {
            "value": h_val,
            "unit": h_unit,
            "effective": h_time,
            "observationId": h_id
        },
        "weight": None if w_val is None else {
            "value": w_val,
            "unit": w_unit,
            "effective": w_time,
            "observationId": w_id
        },
        "bloodPressure": None if not bp_time else {
            "systolic": sys_val,
            "diastolic": dia_val,
            "unit": unit_bp,
            "effective": bp_time,
            "observationId": bp_id
        }
    }
