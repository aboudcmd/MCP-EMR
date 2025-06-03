#!/bin/bash

echo "🚀 Starting EMR Chatbot System in development mode..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run ./scripts/setup.sh first."
    exit 1
fi

# Export environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check for Groq API key
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ GROQ_API_KEY not set in .env file"
    exit 1
fi

# Start services with docker-compose
echo "Starting Docker services..."
docker-compose up -d fhir-db fhir-server

# Wait for FHIR server to be ready
echo "Waiting for FHIR server to be ready..."
sleep 15  # Increased wait time

# Start local development servers
echo "Starting development servers..."

# Start MCP server in background
cd mcp-server && npm run dev &
MCP_PID=$!

# Start backend API in background
cd ../backend-api && npm run dev &
BACKEND_PID=$!

# Start frontend
cd ../frontend && npm run dev &
FRONTEND_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $MCP_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    docker-compose down
}

trap cleanup EXIT

echo "✅ All services started!"
echo "Frontend: http://localhost:3000"  # Fixed port
echo "Backend API: http://localhost:3001"
echo "FHIR Server: http://localhost:8081/fhir"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait