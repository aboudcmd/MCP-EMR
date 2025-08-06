# EMR Backend API Documentation

## Base URL
- Development: Will provide once configured on server
- Production: Configure via environment variable

## Authentication
Currently no authentication required (POC). Production will require JWT tokens.

## Endpoints

### Health Check
```
GET /health
```
Check if the API is running.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-08T10:30:00.000Z",
  "services": {
    "backend": "running",
    "port": 3001
  }
}
```

### Chat
```
POST /api/chat
```
Send a message to the EMR assistant.

**Request:**
```json
{
  "message": "Search for patient John Smith",
  "conversationHistory": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant", 
      "content": "Hi! I'm your EMR assistant."
    }
  ]
}
```

**Required Fields:**
- `message`: The user's message (string)

**Optional Fields:**
- `conversationHistory`: Array of previous messages for context

**Response:**
```json
{
  "response": "I found patient John Smith...",
  "conversationHistory": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! I'm your EMR assistant."
    },
    {
      "role": "user", 
      "content": "Search for patient John Smith"
    },
    {
      "role": "assistant",
      "content": "I found patient John Smith..."
    }
  ]
}
```

## Message Format
Each message has:
- `role`: Either "user" or "assistant"
- `content`: The message text

## Conversation History
**Important**: Always send the complete conversation history with each request to maintain context. The backend returns an updated history that includes your new message and the response.

## Error Responses
- `422`: Validation error (missing required fields)
- `500`: Server error

## Example Usage

### curl
```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for patient John Doe",
    "conversationHistory": []
  }'
```

## Supported Medical Queries
- Patient search by name, ID, National ID, or Iqama
- Patient details and demographics
- Medical conditions and diagnoses
- Current medications
- Lab results and observations
- Visit history and encounters
- Allergies and intolerances

## Production Notes
For production deployment:
- Add JWT authentication headers
- Enable request/response logging, such as logging ChatId
- Set up proper CORS origins
- Configure environment variables
- Implement rate limiting