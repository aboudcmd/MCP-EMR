// Example API service with patient ID support
// The frontend team should integrate this pattern

import axios from 'axios';
import { Message } from '../components/ChatInterface';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

export async function sendMessageWithPatient(
  message: string,
  patientId: string,  // Patient ID from dropdown selection
  conversationHistory: Message[]
) {
  const response = await axios.post(`${API_URL}/api/chat`, {
    message,
    patientId,  // Include the patient ID in the request
    conversationHistory: conversationHistory
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        role: m.role,
        content: m.content,
      })),
  });

  return response.data;
}

// Example usage in a component:
// const patientId = selectedPatient.id; // From dropdown
// const response = await sendMessageWithPatient(message, patientId, history);