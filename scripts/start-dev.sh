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

# Start services with docker-compose (skip FHIR server - using external)
echo "Starting Docker services..."
# docker-compose up -d fhir-db fhir-server  # Commented out - using external FHIR server

# Test external FHIR server connection
echo "Testing connection to external FHIR server..."
curl -f http://10.201.205.101:8007/metadata >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Cannot connect to external FHIR server at http://10.201.205.101:8007/"
    echo "Please ensure the Spark FHIR server is running and accessible."
    exit 1
fi
echo "✅ External FHIR server is accessible"

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
    # docker-compose down  # Commented out - no local Docker services running
}

trap cleanup EXIT

echo "✅ All services started!"
echo "Frontend: http://localhost:3000"  # Fixed port
echo "Backend API: http://localhost:3001"
echo "External FHIR Server: http://10.201.205.101:8007/"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait