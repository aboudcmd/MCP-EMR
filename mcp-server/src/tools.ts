export const tools = [
  {
    name: 'search_patients',
    description: 'Search for patients by name, identifier, or other criteria',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Patient name to search for' },
        identifier: { type: 'string', description: 'Patient identifier' },
        birthDate: { type: 'string', description: 'Birth date (YYYY-MM-DD)' },
        gender: { type: 'string', enum: ['male', 'female', 'other'] },
      },
    },
  },
  {
    name: 'get_patient_details',
    description: 'Get detailed information about a specific patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
      },
      required: ['patientId'],
    },
  },
  {
    name: 'get_patient_conditions',
    description: 'Get all conditions/diagnoses for a patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        clinicalStatus: {
          type: 'string',
          enum: ['active', 'recurrence', 'relapse', 'inactive', 'remission', 'resolved'],
        },
      },
      required: ['patientId'],
    },
  },
  {
    name: 'get_patient_medications',
    description: 'Get current medications for a patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        status: { type: 'string', enum: ['active', 'completed', 'stopped'] },
      },
      required: ['patientId'],
    },
  },
  {
    name: 'get_patient_observations',
    description: 'Get observations (vitals, lab results) for a patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        category: { type: 'string', description: 'Category of observation' },
        code: { type: 'string', description: 'LOINC code for specific observation' },
        dateFrom: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
        dateTo: { type: 'string', description: 'End date (YYYY-MM-DD)' },
      },
      required: ['patientId'],
    },
  },
  {
    name: 'get_patient_encounters',
    description: 'Get encounters/visits for a patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        type: { type: 'string', description: 'Type of encounter' },
        dateFrom: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
        dateTo: { type: 'string', description: 'End date (YYYY-MM-DD)' },
      },
      required: ['patientId'],
    },
  },
  {
    name: 'get_patient_allergies',
    description: 'Get allergy and intolerance information for a patient',
    inputSchema: {
      type: 'object',
      properties: {
        patientId: { type: 'string', description: 'FHIR Patient resource ID' },
      },
      required: ['patientId'],
    },
  },
];