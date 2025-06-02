# EMR Chatbot System

A complete EMR chatbot system that uses FHIR, MCP, and Groq LLM to provide natural language access to medical records.

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and add your Groq API key
3. Run the setup script: `./scripts/setup.sh`
4. Start the system: `./scripts/start-dev.sh`
5. Open http://localhost:3000

## Architecture

- **FHIR Server**: HAPI FHIR server for medical data storage
- **MCP Server**: Translates between LLM tools and FHIR API
- **Backend API**: Handles chat requests and LLM communication
- **Frontend**: React-based chat interface

## Development

See individual README files in each service directory for detailed development instructions.