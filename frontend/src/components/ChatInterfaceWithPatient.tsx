import React, { useState } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { sendMessage } from '../services/api';
import { Activity, User } from 'lucide-react';

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function ChatInterfaceWithPatient() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: "Hello! I'm your EMR assistant. Please select a patient or provide a patient ID to get started.",
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');

  // Example patient list - in production, this would come from an API
  const patientOptions = [
    { id: '160278', name: 'John Doe' },
    { id: '360056', name: 'Jane Smith' },
    { id: '57030', name: 'Mohammed Abdullah' },
    { id: '7311', name: 'Sarah Johnson' },
  ];

  const handlePatientChange = (patientId: string) => {
    setSelectedPatientId(patientId);
    // Clear conversation when patient changes
    setMessages([
      {
        id: 1,
        role: 'assistant',
        content: `Patient ${patientId} selected. How can I help you with this patient's information?`,
        timestamp: new Date(),
      },
    ]);
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const updatedMessages = [...messages, userMessage];
      
      // Send with patientId if selected
      const requestBody: any = {
        message: content,
        conversationHistory: updatedMessages
          .filter((m) => m.role !== 'assistant' || !m.content.includes('selected'))
          .map((m) => ({
            role: m.role,
            content: m.content,
          })),
      };

      // Add patientId if selected
      if (selectedPatientId) {
        requestBody.patientId = selectedPatientId;
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3001'}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: updatedMessages.length + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with Patient Selection */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="w-6 h-6 text-blue-600" />
              <h1 className="text-xl font-semibold text-gray-800">EMR Assistant</h1>
            </div>
            
            {/* Patient Selector */}
            <div className="flex items-center space-x-2">
              <User className="w-5 h-5 text-gray-600" />
              <select
                value={selectedPatientId}
                onChange={(e) => handlePatientChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a patient...</option>
                {patientOptions.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.name} (MRN: {patient.id})
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {selectedPatientId && (
            <div className="mt-2 text-sm text-gray-600">
              Current Patient: MRN {selectedPatientId}
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} isLoading={isLoading} />
      </div>

      {/* Input */}
      <MessageInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading}
        placeholder={selectedPatientId ? "Ask about this patient..." : "Select a patient or provide patient ID in your message..."}
      />
    </div>
  );
}