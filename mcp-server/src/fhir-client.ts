import axios, { AxiosInstance } from 'axios';

export class FHIRClient {
  private client: AxiosInstance;

  constructor(baseURL: string, authToken?: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/fhir+json',
        ...(authToken && { Authorization: `Bearer ${authToken}` }),
      },
    });
  }

  async searchPatients(params: any) {
    const queryParams = new URLSearchParams();
    if (params.name) queryParams.append('name', params.name);
    if (params.identifier) queryParams.append('identifier', params.identifier);
    if (params.birthDate) queryParams.append('birthdate', params.birthDate);
    if (params.gender) queryParams.append('gender', params.gender);

    const response = await this.client.get(`/Patient?${queryParams}`);
    return this.formatBundle(response.data);
  }

  async getPatientDetails(patientId: string) {
    const response = await this.client.get(`/Patient/${patientId}`);
    return this.formatPatient(response.data);
  }

  async getPatientConditions(patientId: string, clinicalStatus?: string) {
    const queryParams = new URLSearchParams({ patient: patientId });
    if (clinicalStatus) queryParams.append('clinical-status', clinicalStatus);

    const response = await this.client.get(`/Condition?${queryParams}`);
    return this.formatConditions(response.data);
  }

  async getPatientMedications(patientId: string, status?: string) {
    const queryParams = new URLSearchParams({ patient: patientId });
    if (status) queryParams.append('status', status);

    const response = await this.client.get(`/MedicationRequest?${queryParams}`);
    return this.formatMedications(response.data);
  }

  async getPatientObservations(params: any) {
    const queryParams = new URLSearchParams({ patient: params.patientId });
    if (params.category) queryParams.append('category', params.category);
    if (params.code) queryParams.append('code', params.code);
    if (params.dateFrom || params.dateTo) {
      const dateRange = [];
      if (params.dateFrom) dateRange.push(`ge${params.dateFrom}`);
      if (params.dateTo) dateRange.push(`le${params.dateTo}`);
      queryParams.append('date', dateRange.join(','));
    }

    const response = await this.client.get(`/Observation?${queryParams}`);
    return this.formatObservations(response.data);
  }

  async getPatientEncounters(params: any) {
    const queryParams = new URLSearchParams({ patient: params.patientId });
    if (params.type) queryParams.append('type', params.type);
    if (params.dateFrom || params.dateTo) {
      const dateRange = [];
      if (params.dateFrom) dateRange.push(`ge${params.dateFrom}`);
      if (params.dateTo) dateRange.push(`le${params.dateTo}`);
      queryParams.append('date', dateRange.join(','));
    }

    const response = await this.client.get(`/Encounter?${queryParams}`);
    return this.formatEncounters(response.data);
  }

  async getPatientAllergies(patientId: string) {
    const response = await this.client.get(`/AllergyIntolerance?patient=${patientId}`);
    return this.formatAllergies(response.data);
  }

  // Formatting methods to simplify FHIR responses
  private formatBundle(bundle: any) {
    if (!bundle.entry) return { total: 0, results: [] };
    
    return {
      total: bundle.total || 0,
      results: bundle.entry.map((entry: any) => this.formatPatient(entry.resource)),
    };
  }

  private formatPatient(patient: any) {
    return {
      id: patient.id,
      name: patient.name?.[0]?.given?.join(' ') + ' ' + patient.name?.[0]?.family,
      birthDate: patient.birthDate,
      gender: patient.gender,
      identifier: patient.identifier?.[0]?.value,
      phone: patient.telecom?.find((t: any) => t.system === 'phone')?.value,
      address: patient.address?.[0],
    };
  }

  private formatConditions(bundle: any) {
    if (!bundle.entry) return [];
    
    return bundle.entry.map((entry: any) => ({
      id: entry.resource.id,
      code: entry.resource.code?.coding?.[0]?.display || entry.resource.code?.text,
      clinicalStatus: entry.resource.clinicalStatus?.coding?.[0]?.code,
      onsetDateTime: entry.resource.onsetDateTime,
      recordedDate: entry.resource.recordedDate,
    }));
  }

  private formatMedications(bundle: any) {
    if (!bundle.entry) return [];
    
    return bundle.entry.map((entry: any) => ({
      id: entry.resource.id,
      medication: entry.resource.medicationCodeableConcept?.text ||
                  entry.resource.medicationCodeableConcept?.coding?.[0]?.display,
      status: entry.resource.status,
      dosage: entry.resource.dosageInstruction?.[0]?.text,
      authoredOn: entry.resource.authoredOn,
    }));
  }

  private formatObservations(bundle: any) {
    if (!bundle.entry) return [];
    
    return bundle.entry.map((entry: any) => ({
      id: entry.resource.id,
      type: entry.resource.code?.coding?.[0]?.display || entry.resource.code?.text,
      value: entry.resource.valueQuantity?.value + ' ' + entry.resource.valueQuantity?.unit,
      effectiveDateTime: entry.resource.effectiveDateTime,
      status: entry.resource.status,
    }));
  }

  private formatEncounters(bundle: any) {
    if (!bundle.entry) return [];
    
    return bundle.entry.map((entry: any) => ({
      id: entry.resource.id,
      type: entry.resource.type?.[0]?.text,
      status: entry.resource.status,
      period: entry.resource.period,
      serviceProvider: entry.resource.serviceProvider?.display,
    }));
  }

  private formatAllergies(bundle: any) {
    if (!bundle.entry) return [];
    
    return bundle.entry.map((entry: any) => ({
      id: entry.resource.id,
      substance: entry.resource.code?.coding?.[0]?.display || entry.resource.code?.text,
      criticality: entry.resource.criticality,
      type: entry.resource.type,
      recordedDate: entry.resource.recordedDate,
    }));
  }
}