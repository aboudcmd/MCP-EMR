import axios from 'axios';
import { Message } from '../components/ChatInterface';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

export async function sendMessage(
  message: string,
  conversationHistory: Message[],
  patientId?: string
) {
  const requestBody: any = {
    message,
    conversationHistory: conversationHistory
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        role: m.role,
        content: m.content,
      })),
  };

  // Add patientId if provided
  if (patientId && patientId.trim()) {
    requestBody.patientId = patientId.trim();
  }

  const response = await axios.post(`${API_URL}/api/chat`, requestBody);

  return response.data;
}