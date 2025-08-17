# EMR Chatbot System

An AI-powered Electronic Medical Records (EMR) assistant that provides intelligent access to patient data through natural language queries.

## Features

- **Patient-Specific Queries**: Query patient data by providing a patient ID
- **Comprehensive Medical Data Access**:
  - Patient demographics and information
  - Medical conditions and diagnoses
  - Medications and prescriptions
  - Vital signs and observations
  - Allergies and intolerances
  - Encounters and visits
- **FHIR Compliant**: Integrates with FHIR-compliant servers
- **Natural Language Processing**: Powered by Groq LLM for intelligent responses

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend  │────▶│  Backend API │────▶│  MCP Server  │────▶│ FHIR Server  │
│   (React)   │     │   (FastAPI)  │     │   (Python)   │     │   (Spark)    │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Groq API Key
- Access to a FHIR server

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd emr-chatbot-system
   ```

2. **Create `.env` file**
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   FHIR_SERVER_URL=http://your-fhir-server:port/
   FHIR_USERNAME=your_username
   FHIR_PASSWORD=your_password
   ```

3. **Start the services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3004
   - Backend API: http://localhost:8004
   - MCP Server: http://localhost:8888

## Usage

### With Patient ID Input
1. Enter a patient ID in the input field (e.g., "7311")
2. Ask questions like:
   - "What are their conditions?"
   - "Show me their latest vitals"
   - "What medications are they on?"

### Without Patient ID
Include the patient ID in your message:
- "What are patient 7311's conditions?"
- "Show vitals for patient 160278"

## API Endpoints

### Health Check
```
GET /health
```

### Chat Endpoint
```
POST /api/chat
{
  "message": "string",
  "patientId": "string (optional)",
  "conversationHistory": []
}
```

## Project Structure

```
emr-chatbot-system/
├── backend-api-python/     # FastAPI backend service
│   ├── main.py            # Main API server
│   ├── groq_client.py     # Groq LLM client
│   └── http_mcp_client.py # MCP server client
├── mcp-server-python/      # MCP server for FHIR integration
│   ├── main.py            # MCP HTTP server
│   ├── fhir_client.py     # FHIR API client
│   └── types_models.py    # Data models
├── frontend/               # React frontend
│   └── src/
│       ├── components/    # React components
│       └── services/      # API services
├── docker-compose.yml      # Docker orchestration
└── scripts/               # Utility scripts
```

## Development

### Running Locally

1. **Backend API**
   ```bash
   cd backend-api-python
   pip install -r requirements.txt
   python main.py
   ```

2. **MCP Server**
   ```bash
   cd mcp-server-python
   pip install -r requirements.txt
   python main.py
   ```

3. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Testing

Run the API test script:
```bash
./scripts/test-api.sh
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key for LLM | Required |
| `FHIR_SERVER_URL` | FHIR server URL | Required |
| `FHIR_USERNAME` | FHIR server username | Optional |
| `FHIR_PASSWORD` | FHIR server password | Optional |
| `MCP_SERVER_URL` | MCP server URL | http://localhost:8888 |
| `CORS_ORIGIN` | Allowed CORS origin | http://localhost:3004 |

## License

[Your License Here]

## Support

For issues or questions, please open an issue in the repository.