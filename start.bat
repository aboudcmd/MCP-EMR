@echo off
echo Starting Docker services...
docker-compose up -d fhir-server fhir-db

echo Waiting for services...
timeout /t 15

echo Starting development servers...
start "MCP Server" cmd /k "cd mcp-server && npm run dev"
start "Backend API" cmd /k "cd backend-api && npm run dev"
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Services are starting up...
echo Frontend will be available at: http://localhost:3000
echo.
pause