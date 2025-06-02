#!/bin/bash

echo "📊 Loading sample data into FHIR server..."

FHIR_URL="http://localhost:8081/fhir"

# Load patients
for file in sample-data/patients/*.json; do
    echo "Loading patient from $file..."
    curl -X POST "$FHIR_URL/Patient" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
done

# Load conditions
for file in sample-data/conditions/*.json; do
    echo "Loading condition from $file..."
    curl -X POST "$FHIR_URL/Condition" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
done

# Load medications
for file in sample-data/medications/*.json; do
    echo "Loading medication from $file..."
    curl -X POST "$FHIR_URL/MedicationRequest" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
done

# Load observations
for file in sample-data/observations/*.json; do
    echo "Loading observation from $file..."
    curl -X POST "$FHIR_URL/Observation" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
done

echo "✅ Sample data loaded!"