# Patient Context Update Documentation

## Overview
The EMR Chatbot has been updated to support patient-specific context, where all queries are limited to a single patient selected from the frontend.

## API Changes

### Chat Endpoint
**Endpoint:** `POST /api/chat`

#### Request Body Structure (Updated)
```json
{
  "message": "string",
  "patientId": "string",  // NEW: Required patient ID/MRN
  "conversationHistory": [
    {
      "role": "user|assistant",
      "content": "string"
    }
  ]
}
```

#### Key Changes:
1. **Required `patientId` field**: Must be provided with every request
2. **Validation**: Patient ID must be 4-7 digits (configurable)
3. **Context Isolation**: All queries will be executed only for the specified patient

## Frontend Integration

### Required Changes:
1. **Add patient dropdown/selector** to the UI
2. **Pass selected patient ID** with every chat request
3. **Clear conversation** when patient selection changes

### Example Implementation:
```typescript
// api.ts
export async function sendMessage(
  message: string,
  patientId: string,  // From patient selector
  conversationHistory: Message[]
) {
  const response = await axios.post(`${API_URL}/api/chat`, {
    message,
    patientId,
    conversationHistory
  });
  return response.data;
}

// Component usage
const handleSendMessage = async (message: string) => {
  if (!selectedPatientId) {
    alert('Please select a patient first');
    return;
  }
  
  const response = await sendMessage(
    message,
    selectedPatientId,
    conversationHistory
  );
  // Handle response...
};
```

## Benefits

1. **Prevents Cross-Patient Data Leakage**: Each session is isolated to one patient
2. **Improved Security**: No accidental queries about wrong patients
3. **Better User Experience**: Clear context about which patient is being discussed
4. **Simplified Follow-up Queries**: System always knows which patient context to use

## Testing

### Test Scenarios:
1. **Valid Patient ID**: Should process normally
2. **Missing Patient ID**: Should return 400 error
3. **Invalid Format**: Should return validation error
4. **Patient Switch**: Should clear previous context

### Example Test Requests:

#### Valid Request:
```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the patient conditions?",
    "patientId": "160278",
    "conversationHistory": []
  }'
```

#### Error Case (No Patient ID):
```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the conditions?",
    "conversationHistory": []
  }'
# Returns: 400 Bad Request - "Patient ID is required"
```

## Migration Notes

- Existing frontend code needs to be updated to include `patientId`
- Consider adding a patient selector component if not already present
- Update any API client libraries or SDKs
- Test thoroughly with different patient IDs

## Future Enhancements

- Add patient name display for confirmation
- Support for multiple patient comparison (future version)
- Patient ID autocomplete/search functionality
- Session management per patient