#!/bin/bash

echo "🧪 Testing EMR Chatbot API..."

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8004/health | jq .

# Test chat endpoint with patient ID
echo -e "\nTesting chat endpoint with patient ID..."
curl -s -X POST http://localhost:8004/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are their conditions?",
    "patientId": "7311",
    "conversationHistory": []
  }' | jq .

echo -e "\n✅ API tests complete!"