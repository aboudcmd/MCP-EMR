import axios from 'axios';

const API_URL = 'http://localhost:8004';

// Store session ID in localStorage
let sessionId: string | null = localStorage.getItem('emr_session_id');

export async function sendMessage(
  message: string,
  patientId?: string
) {
  const requestBody: any = {
    message,
    sessionId,
    patientId: patientId?.trim() || undefined
  };

  try {
    const response = await axios.post(`${API_URL}/api/chat`, requestBody);
    
    // Store session ID if new one created
    if (response.data.sessionId) {
      sessionId = response.data.sessionId;
      localStorage.setItem('emr_session_id', response.data.sessionId);
    }
    
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export function clearSession() {
  if (sessionId) {
    axios.delete(`${API_URL}/api/session/${sessionId}`).catch(console.error);
    localStorage.removeItem('emr_session_id');
    sessionId = null;
  }
}