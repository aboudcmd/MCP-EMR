from pydantic import BaseModel
from typing import Optional

class SearchPatientsArgs(BaseModel):
    name: Optional[str] = None
    mrn: Optional[str] = None  # Medical Record Number
    nationalId: Optional[str] = None  # Saudi National ID
    iqama: Optional[str] = None  # Iqama number for residents
    birthDate: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class GetPatientDetailsArgs(BaseModel):
    patientId: str

class GetPatientConditionsArgs(BaseModel):
    patientId: str
    clinicalStatus: Optional[str] = None

class GetPatientMedicationsArgs(BaseModel):
    patientId: str
    status: Optional[str] = None

class GetPatientObservationsArgs(BaseModel):
    patientId: str
    category: Optional[str] = None
    code: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None

class GetPatientEncountersArgs(BaseModel):
    patientId: str
    type: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None

class GetPatientAllergiesArgs(BaseModel):
    patientId: str