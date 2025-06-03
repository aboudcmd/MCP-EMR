import dotenv from 'dotenv';
import { FHIRClient } from './fhir-client';
import { tools } from './tools';
import {
  SearchPatientsArgs,
  GetPatientDetailsArgs,
  GetPatientConditionsArgs,
  GetPatientMedicationsArgs,
  GetPatientObservationsArgs,
  GetPatientEncountersArgs,
  GetPatientAllergiesArgs
} from './types';

dotenv.config();

const fhirClient = new FHIRClient(
  process.env.FHIR_SERVER_URL || 'http://localhost:8081/fhir'
);

// MCP Server implementation for tool execution
export async function executeTool(toolName: string, args: any) {
  switch (toolName) {
    case 'search_patients':
      return await fhirClient.searchPatients(args as SearchPatientsArgs);
    
    case 'get_patient_details':
      return await fhirClient.getPatientDetails((args as GetPatientDetailsArgs).patientId);
    
    case 'get_patient_conditions':
      const condArgs = args as GetPatientConditionsArgs;
      return await fhirClient.getPatientConditions(condArgs.patientId, condArgs.clinicalStatus);
    
    case 'get_patient_medications':
      const medArgs = args as GetPatientMedicationsArgs;
      return await fhirClient.getPatientMedications(medArgs.patientId, medArgs.status);
    
    case 'get_patient_observations':
      return await fhirClient.getPatientObservations(args as GetPatientObservationsArgs);
    
    case 'get_patient_encounters':
      return await fhirClient.getPatientEncounters(args as GetPatientEncountersArgs);
    
    case 'get_patient_allergies':
      return await fhirClient.getPatientAllergies((args as GetPatientAllergiesArgs).patientId);
    
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

// Handle incoming requests when run as a standalone process
if (require.main === module) {
  process.stdin.on('data', async (data) => {
    try {
      const request = JSON.parse(data.toString());
      const result = await executeTool(request.params.name, request.params.arguments);
      
      const response = {
        jsonrpc: '2.0',
        result,
        id: request.id
      };
      
      console.log(JSON.stringify(response));
      process.exit(0);
    } catch (error: any) {
      const errorResponse = {
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: error.message
        },
        id: 1
      };
      console.error(JSON.stringify(errorResponse));
      process.exit(1);
    }
  });
}