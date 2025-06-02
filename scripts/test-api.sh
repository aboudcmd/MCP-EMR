#!/bin/bash

echo "🧪 Testing EMR Chatbot API..."

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:3001/health | jq .

# Test chat endpoint
echo -e "\nTesting chat endpoint..."
curl -s -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find patients named Smith"
  }' | jq .

echo -e "\n✅ API tests complete!"