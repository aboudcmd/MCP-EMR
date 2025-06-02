#!/bin/bash
set -e

echo "🏥 Setting up EMR Chatbot System..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting." >&2; exit 1; }

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your Groq API key!"
fi

# Install dependencies for each service
echo "Installing MCP Server dependencies..."
cd mcp-server && npm install && cd ..

echo "Installing Backend API dependencies..."
cd backend-api && npm install && cd ..

echo "Installing Frontend dependencies..."
cd frontend && npm install && cd ..

# Build TypeScript projects
echo "Building MCP Server..."
cd mcp-server && npm run build && cd ..

echo "Building Backend API..."
cd backend-api && npm run build && cd ..

echo "✅ Setup complete! Run ./scripts/start-dev.sh to start the development environment."