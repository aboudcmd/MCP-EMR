export interface SearchPatientsArgs {
  name?: string;
  identifier?: string;
  birthDate?: string;
  gender?: 'male' | 'female' | 'other';
}

export interface GetPatientDetailsArgs {
  patientId: string;
}

export interface GetPatientConditionsArgs {
  patientId: string;
  clinicalStatus?: 'active' | 'recurrence' | 'relapse' | 'inactive' | 'remission' | 'resolved';
}

export interface GetPatientMedicationsArgs {
  patientId: string;
  status?: 'active' | 'completed' | 'stopped';
}

export interface GetPatientObservationsArgs {
  patientId: string;
  category?: string;
  code?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface GetPatientEncountersArgs {
  patientId: string;
  type?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface GetPatientAllergiesArgs {
  patientId: string;
}