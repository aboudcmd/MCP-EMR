import axios from 'axios';

const API_URL = 'http://10.7.1.9:8004';

export async function sendMessage(
  message: string,
  patientId?: string
) {
  const requestBody: any = {
    message,
    patientId: patientId?.trim() || undefined
  };

  try {
    const response = await axios.post(`${API_URL}/api/chat`, requestBody);
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export function clearPatientSession(patientId: string) {
  return axios.delete(`${API_URL}/api/patient/${patientId}/session`).catch(console.error);
}