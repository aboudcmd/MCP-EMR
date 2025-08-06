@echo off
echo === Loading All Sample Data ===
echo.

set FHIR_URL=http://10.201.205.101:8007/
cd ..

echo [1/6] Loading Patients...
echo ------------------------
for %%f in (sample-data\patients\*.json) do (
    echo Loading %%~nf...
    curl -X PUT "%FHIR_URL%/Patient/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
    echo.
    timeout /t 1 >nul
)

echo.
echo [2/6] Loading Conditions...
echo --------------------------
for %%f in (sample-data\conditions\*.json) do (
    echo Loading %%~nf...
    curl -X PUT "%FHIR_URL%/Condition/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
    echo.
    timeout /t 1 >nul
)

echo.
echo [3/6] Loading Medications...
echo ----------------------------
for %%f in (sample-data\medications\*.json) do (
    echo Loading %%~nf...
    curl -X PUT "%FHIR_URL%/MedicationRequest/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
    echo.
    timeout /t 1 >nul
)

echo.
echo [4/6] Loading Observations...
echo -----------------------------
for %%f in (sample-data\observations\*.json) do (
    echo Loading %%~nf...
    curl -X PUT "%FHIR_URL%/Observation/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
    echo.
    timeout /t 1 >nul
)

echo.
echo [5/6] Loading Encounters (if exists)...
echo ---------------------------------------
if exist sample-data\encounters\*.json (
    for %%f in (sample-data\encounters\*.json) do (
        echo Loading %%~nf...
        curl -X PUT "%FHIR_URL%/Encounter/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
        echo.
        timeout /t 1 >nul
    )
) else (
    echo No encounter files found, skipping...
)

echo.
echo [6/6] Loading Allergies (if exists)...
echo --------------------------------------
if exist sample-data\allergies\*.json (
    for %%f in (sample-data\allergies\*.json) do (
        echo Loading %%~nf...
        curl -X PUT "%FHIR_URL%/AllergyIntolerance/%%~nf" -H "Content-Type: application/fhir+json" -d @%%f
        echo.
        timeout /t 1 >nul
    )
) else (
    echo No allergy files found, skipping...
)

echo.
echo === Verifying Data Load ===
echo.
echo Counting resources...
curl -s "%FHIR_URL%/Patient?_summary=count" | findstr /C:"\"total\""
curl -s "%FHIR_URL%/Condition?_summary=count" | findstr /C:"\"total\""
curl -s "%FHIR_URL%/MedicationRequest?_summary=count" | findstr /C:"\"total\""
curl -s "%FHIR_URL%/Observation?_summary=count" | findstr /C:"\"total\""

echo.
echo === Data Loading Complete! ===
echo.
echo You can now test the chatbot with queries like:
echo - "Find all patients"
echo - "Show me patient John Smith"
echo - "What conditions does Sarah Johnson have?"
echo - "Show medications for patient-003"
echo.
cd scripts
pause