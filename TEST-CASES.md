# EMR Chatbot Test Cases

Test these queries with patient ID: **450812**

---

## 1. Laboratory Tests (Category Filtering)

### Basic Lab Queries
- [ ] "Show me the patient's lab results"
- [ ] "What are the latest lab tests?"
- [ ] "Get all laboratory results"

### Specific Lab Tests
- [ ] "Show me the last 5 CBC results"
- [ ] "What's the patient's hemoglobin level?"
- [ ] "Show me cholesterol results"
- [ ] "What are the HDL and LDL values?"
- [ ] "Get glucose/blood sugar levels"
- [ ] "Show me liver function tests (AST/ALT)"

### Expected Behavior:
✅ Should use `category="laboratory"` filter
✅ Should return only lab results (not vitals or imaging)
✅ Should show multiple results if available
✅ Should show most recent first

---

## 2. Vital Signs (Category Filtering)

### Basic Vitals Queries
- [ ] "What are the patient's vitals?"
- [ ] "Show me vital signs"
- [ ] "What's the latest blood pressure?"
- [ ] "Show me the patient's weight history"
- [ ] "What's the heart rate?"
- [ ] "Show temperature readings"

### Trend Analysis
- [ ] "Show me blood pressure trends over time"
- [ ] "Has the patient's weight changed?"
- [ ] "Compare vitals from the last 3 visits"

### Expected Behavior:
✅ Should use `category="vital-signs"` filter
✅ Should return only vitals (BP, weight, temp, HR, etc.)
✅ Should handle component values (systolic/diastolic BP)

---

## 3. Radiology/Imaging (Category Filtering)

### Basic Imaging Queries
- [ ] "Show me radiology reports"
- [ ] "What imaging studies has this patient had?"
- [ ] "Show me X-ray results"
- [ ] "Any CT or MRI findings?"
- [ ] "Show me the foot X-ray report"

### Expected Behavior:
✅ Should use `category="imaging"` filter
✅ Should return text-based radiology interpretations
✅ Should show full report text (valueString)

---

## 4. Mixed Queries (No Category Filter)

### General Queries
- [ ] "Show me all observations"
- [ ] "What tests has this patient had?"
- [ ] "Give me a summary of all results"

### Expected Behavior:
✅ Should NOT use category filter
✅ Should return mixed results (vitals, labs, imaging)
✅ Should categorize results in response (vitals, labs, imaging sections)

---

## 5. Date Range Filtering

### Recent Results
- [ ] "Show me lab results from the last month"
- [ ] "What are the vitals from 2024?"
- [ ] "Show me imaging from the past year"

### Specific Date Ranges
- [ ] "Show me labs between January 2024 and March 2024"
- [ ] "What were the vitals in November 2024?"
- [ ] "Show me all results from 2023"

### Expected Behavior:
✅ Should use `dateFrom` and/or `dateTo` parameters
✅ Should filter results to specified date range
✅ Should work in combination with category filters

---

## 6. Multiple Parameter Combinations

### Advanced Filtering
- [ ] "Show me lab results from 2024"
  (category="laboratory" + dateFrom="2024-01-01")

- [ ] "What were the vitals in the last 6 months?"
  (category="vital-signs" + dateFrom="2024-06-01")

- [ ] "Show me imaging reports from 2018"
  (category="imaging" + dateFrom="2018-01-01" + dateTo="2018-12-31")

### Expected Behavior:
✅ Should combine multiple filters correctly
✅ Should apply both category AND date filters simultaneously

---

## 7. Other Patient Data (Non-Observation Tools)

### Patient Demographics
- [ ] "Show me patient details"
- [ ] "What's the patient's name and age?"
- [ ] "Get patient contact information"

### Expected Tool:
✅ Should use `get_patient_details` (not observations)

### Medical Conditions
- [ ] "What conditions does this patient have?"
- [ ] "Show me diagnoses"
- [ ] "Any chronic diseases?"

### Expected Tool:
✅ Should use `get_patient_conditions` (not observations)

### Medications
- [ ] "What medications is the patient taking?"
- [ ] "Show me prescriptions"
- [ ] "Any current drugs?"

### Expected Tool:
✅ Should use `get_patient_medications` (not observations)

### Allergies
- [ ] "Does the patient have any allergies?"
- [ ] "Show me allergy information"
- [ ] "Any drug allergies?"

### Expected Tool:
✅ Should use `get_patient_allergies` (not observations)

---

## 8. Edge Cases & Error Handling

### Ambiguous Queries
- [ ] "Show me results"
  (Should ask for clarification or show all observations)

- [ ] "What tests?"
  (Should ask which type: labs, imaging, vitals?)

### No Results Scenarios
- [ ] "Show me labs from 1990"
  (Should gracefully handle no results)

- [ ] "Show me MRI results"
  (If patient has no MRIs, should say so clearly)

### Invalid Date Formats
- [ ] "Show me labs from last week"
  (LLM should convert to proper date format)

- [ ] "What were vitals yesterday?"
  (Should calculate relative date)

### Expected Behavior:
✅ Should handle missing data gracefully
✅ Should ask clarifying questions when needed
✅ Should convert relative dates to absolute dates
✅ Should not crash or return errors to user

---

## 9. Context & Follow-up Questions

### Conversational Context
1. "Show me the patient's lab results"
2. [ ] "What about the CBC specifically?"
   (Should maintain context of labs)

3. [ ] "And the most recent one?"
   (Should maintain context of CBC labs)

### Expected Behavior:
✅ Should maintain conversation context
✅ Should refine previous query with new constraints
✅ Should not require repeating patient ID

---

## 10. Performance & Limits

### Large Result Sets
- [ ] "Show me all observations" (should return up to 200)
- [ ] "Show me all lab results" (should return up to 200 labs only)

### Pagination Awareness
- [ ] Ask: "Are there more results beyond the 200 shown?"
  (LLM should acknowledge the limit if total > 200)

### Expected Behavior:
✅ Should retrieve 200 observations (up from 100)
✅ Should indicate if results are truncated
✅ Should suggest filtering if too many results

---

## 11. Clinical Reasoning

### Interpretation Queries
- [ ] "Are the CBC values normal?"
- [ ] "Is the cholesterol level concerning?"
- [ ] "Interpret the blood pressure readings"
- [ ] "What do these lab results indicate?"

### Expected Behavior:
✅ Should retrieve relevant observations
✅ Should provide clinical context (reference ranges)
✅ Should compare to normal ranges when available
⚠️  Should include disclaimer about clinical interpretation

---

## 12. Multi-Step Queries

### Complex Information Gathering
- [ ] "Give me a complete health summary including vitals, labs, medications, and conditions"

### Expected Behavior:
✅ Should call multiple tools (4+ tool calls)
✅ Should organize response by category
✅ Should handle sequential tool execution

---

## Testing Checklist

### Before Testing:
- [ ] Backend API is running: `docker-compose restart backend-api`
- [ ] MCP Server has hot reload enabled
- [ ] Patient ID 450812 exists in FHIR database
- [ ] Test data includes vitals, labs, and imaging observations

### During Testing - Watch Logs:
```bash
# Watch backend logs
docker-compose logs -f backend-api

# Watch MCP server logs
docker-compose logs -f mcp-server
```

### Look For:
- [ ] Tool calls show correct category parameter
- [ ] `category="laboratory"` when asking for labs
- [ ] `category="vital-signs"` when asking for vitals
- [ ] `category="imaging"` when asking for radiology
- [ ] Date filters applied when date ranges mentioned
- [ ] 200 observations retrieved (not 100)

---

## Expected Log Output Example:

### ✅ Good - Category Filter Used:
```
🔧 Async tool: get_patient_observations called with patient_id=450812, category=laboratory, code=None
```

### ❌ Bad - No Filter (when it should):
```
🔧 Async tool: get_patient_observations called with patient_id=450812, category=None, code=None
```

---

## Scoring Rubric

Rate each category:
- **🟢 Pass**: Correct tool, correct parameters, accurate results
- **🟡 Partial**: Correct results but suboptimal tool usage
- **🔴 Fail**: Wrong tool, wrong results, or error

### Target Scores:
- Laboratory Tests: 90%+ pass rate
- Vital Signs: 90%+ pass rate
- Imaging: 90%+ pass rate
- Date Filtering: 80%+ pass rate
- Mixed Queries: 85%+ pass rate
- Other Tools: 95%+ pass rate

---

## Quick Smoke Test (Run These First)

1. [ ] "Show me lab results" → Should filter to labs only
2. [ ] "Show me vitals" → Should filter to vitals only
3. [ ] "Show me X-rays" → Should filter to imaging only
4. [ ] "Show me medications" → Should use medications tool (not observations)
5. [ ] "Show me last 5 CBC results" → Should return multiple CBC results

**If all 5 pass:** ✅ System is working correctly
**If any fail:** ⚠️ Review logs and check tool routing

---

## Troubleshooting

### If category filter not being used:
1. Check tool description mentions category parameter
2. Verify LangChain tool has `PatientObservationsInput` schema
3. Restart backend: `docker-compose restart backend-api`

### If no results returned:
1. Verify patient 450812 has data in FHIR server
2. Check FHIR server is accessible
3. Review MCP server logs for errors

### If wrong tool called:
1. Review tool descriptions for ambiguity
2. Check if query is clear enough
3. Consider updating tool descriptions

---

## Success Criteria

✅ **Filtering Works**: Category parameter used correctly 80%+ of the time
✅ **Correct Tool Selection**: Right tool chosen 95%+ of the time
✅ **Results Quality**: Relevant results returned, properly formatted
✅ **Performance**: Responses within 3-5 seconds
✅ **Limit Increase**: Able to retrieve 200 observations instead of 100
✅ **Error Handling**: Graceful handling of edge cases and missing data
