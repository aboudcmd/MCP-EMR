# Error Handling Improvements

## Overview
Enhanced error handling across all layers to provide user-friendly, actionable error messages instead of raw technical errors.

---

## Changes Made

### **1. FHIR Client Layer** (`fhir_client.py`)

#### Before:
```
Exception: Client error '400 Bad Request' for url 'http://...'
For more information check: https://developer.mozilla.org/...
```

#### After:
```python
# Parse FHIR OperationOutcome for detailed error info
# Map HTTP status codes to user-friendly messages:

400 → "Invalid request parameters. [details]"
401 → "Authentication failed. Please check credentials."
403 → "Access denied. You don't have permission..."
404 → "Resource not found: [path]"
500 → "FHIR server error. Please try again or contact support."
503 → "FHIR server is temporarily unavailable..."
Timeout → "Request timed out..."
Connection → "Cannot connect to FHIR server..."
```

**Location:** `fhir_client.py` lines 78-120

---

### **2. MCP Server Layer** (`main.py`)

#### Before:
```
Exception: Tool execution failed: Client error '400 Bad Request'...
```

#### After:
```python
# Categorize exceptions and add context:

ValueError → "Invalid request: [details]"
PermissionError → "Access denied: [details]"
FileNotFoundError → "Patient or resource not found (ID: 450812). Please verify..."
TimeoutError → "The request timed out. Please try again."
ConnectionError → "Cannot connect to the medical records system..."
RuntimeError → "Medical records system error: [details]"
Exception → "An unexpected error occurred. Please try again..."
```

**Location:** `main.py` lines 129-163

---

### **3. Tools Layer** (`tools_async.py`)

#### Before:
```
Error retrieving observations: MCP error: Tool execution failed...
```

#### After:
```python
# Build contextual error messages:

"Unable to retrieve laboratory results for patient 450812.
Invalid request parameters. [FHIR error details]"

"Unable to retrieve vital signs from 2024-01-01 onwards for patient 450812.
The request timed out. Please try again."

"Unable to retrieve imaging/radiology reports from 2024-01-01 to 2024-12-31...
Patient or resource not found..."
```

**Location:** `tools_async.py` lines 197-221

---

## Error Flow Example

### **Scenario:** Invalid date parameter causes 400 error

#### **Old Flow:**
```
1. FHIR Server: 400 Bad Request
   ↓
2. FHIR Client: httpx.HTTPStatusError
   ↓
3. MCP Server: Exception("Tool execution failed: Client error '400 Bad Request'...")
   ↓
4. Tools Layer: "Error retrieving observations: MCP error: Tool execution..."
   ↓
5. LLM sees: Raw technical error
   ↓
6. User sees: "I'm experiencing a technical issue..."
```

#### **New Flow:**
```
1. FHIR Server: 400 Bad Request with OperationOutcome
   ↓
2. FHIR Client: Parses error, extracts details
                Raises ValueError("Invalid request parameters. Date format must be YYYY-MM-DD")
   ↓
3. MCP Server: Catches ValueError
                Adds context: "Invalid request: Date format must be YYYY-MM-DD"
   ↓
4. Tools Layer: Catches exception
                 Adds context: "Unable to retrieve laboratory results from 2024-50-99 for patient 450812"
                 Returns: "Invalid request: Date format must be YYYY-MM-DD"
   ↓
5. LLM sees: Clear, actionable error
   ↓
6. User sees: "The date format you provided is invalid. Please use YYYY-MM-DD format."
```

---

## Error Message Types

### **1. Invalid Parameters (400)**
```
User Query: "Show me labs from 2024-50-50"
Error Message: "Unable to retrieve laboratory results for patient 450812.
Invalid request parameters. Invalid date format."
```

### **2. Authentication/Authorization (401/403)**
```
User Query: "Show me patient 12345 labs"
Error Message: "Unable to retrieve laboratory results for patient 12345.
Access denied. You don't have permission to access this resource."
```

### **3. Not Found (404)**
```
User Query: "Show me data for patient 99999"
Error Message: "Patient or resource not found (ID: 99999).
Please verify the patient ID is correct."
```

### **4. Server Error (500)**
```
User Query: "Show me labs"
Error Message: "Unable to retrieve laboratory results for patient 450812.
FHIR server error. Please try again or contact support."
```

### **5. Timeout**
```
User Query: "Show me all observations"
Error Message: "Unable to retrieve observations for patient 450812.
The request timed out. Please try again."
```

### **6. Connection Error**
```
User Query: "Show me vitals"
Error Message: "Unable to retrieve vital signs for patient 450812.
Cannot connect to the medical records system. Please contact your administrator."
```

---

## Benefits

### ✅ **User-Friendly**
- Plain English, no HTTP status codes
- Explains what went wrong
- Provides actionable next steps

### ✅ **Contextual**
- Shows what data was being retrieved
- Includes patient ID
- Shows date ranges if applicable
- Shows category (labs, vitals, imaging)

### ✅ **Actionable**
- Suggests fixes ("Please verify patient ID")
- Recommends next steps ("Try again" vs "Contact admin")
- Differentiates transient vs permanent errors

### ✅ **Debuggable**
- Technical details still logged to server
- Error details preserved for debugging
- Maintains full exception traceback in logs

### ✅ **LLM-Friendly**
- Clear error messages help LLM understand what failed
- LLM can explain errors naturally to user
- LLM can suggest alternatives or workarounds

---

## Testing Error Handling

### **Test Cases:**

1. **Invalid Date Format**
   ```
   Query: "Show me labs from last week"
   If LLM converts to invalid date: "2024-50-99"
   Should get: Clear date format error
   ```

2. **Patient Not Found**
   ```
   Query: "Show me patient 99999 data"
   Should get: "Patient not found (ID: 99999)"
   ```

3. **Invalid Category**
   ```
   Query with: category="invalid-category"
   Should get: "Invalid request parameters"
   ```

4. **FHIR Server Down**
   ```
   Stop FHIR server
   Query: "Show me labs"
   Should get: "Cannot connect to medical records system"
   ```

5. **Timeout Simulation**
   ```
   Set FHIR server to be very slow
   Should get: "Request timed out. Please try again."
   ```

---

## Error Logging

### **What Gets Logged:**

#### **FHIR Client:**
```python
logger.error(f"FHIR server error: {status_code} - {response.text[:200]}")
```

#### **MCP Server:**
```python
logger.error(f"Invalid parameters for get_patient_observations: {e}")
logger.error(f"Unexpected error executing tool: {e}", exc_info=True)
```

#### **Tools Layer:**
```python
logger.error(f"Tool error: {e}", exc_info=True)
```

### **What Users See:**
```
"Unable to retrieve laboratory results for patient 450812.
Invalid request parameters. Date format must be YYYY-MM-DD"
```

---

## Configuration

No configuration needed! Error handling is built into the code and works automatically.

The system will:
- ✅ Parse FHIR OperationOutcome errors
- ✅ Map HTTP status codes to friendly messages
- ✅ Add contextual information (patient ID, category, dates)
- ✅ Provide actionable suggestions
- ✅ Log technical details for debugging

---

## Future Improvements

### **Potential Enhancements:**

1. **Error Codes** - Add unique error codes for tracking
   ```
   "Error EMR-001: Patient not found"
   ```

2. **Retry Logic** - Automatic retry for transient errors
   ```python
   if status_code == 503:  # Service Unavailable
       retry after 5 seconds
   ```

3. **Circuit Breaker** - Prevent cascading failures
   ```python
   if too many errors:
       temporarily stop calling FHIR server
   ```

4. **Error Analytics** - Track error rates and types
   ```python
   metrics.increment("fhir.error.404")
   ```

5. **Custom Error Pages** - Show helpful UI for common errors

6. **Error Recovery** - Suggest alternative data sources
   ```
   "Labs not available, but I can show you vitals instead?"
   ```

---

## Restart Services

After these changes, restart the services:

```bash
# MCP server has hot reload, so changes are already live!
# Just restart backend:
docker-compose restart backend-api
```

---

## Success Criteria

✅ **No more raw HTTP errors** shown to users
✅ **Context included** in every error message
✅ **Actionable suggestions** provided
✅ **Technical details logged** for debugging
✅ **LLM can explain** errors naturally
