#!/bin/bash

echo "📊 Loading sample data into FHIR server..."

FHIR_URL="http://10.201.205.101:8007/"

# Helper: given a path like "sample-data/patients/patient-001.json",
# extract "patient-001" (basename without .json)
get_id_from_filename() {
  local filepath="$1"
  # strip directory, then strip .json
  local filename="$(basename "$filepath")"
  echo "${filename%.json}"
}

# Load patients
for file in sample-data/patients/*.json; do
  if [ -f "$file" ]; then
    id="$(get_id_from_filename "$file")"
    echo "Loading patient with ID=$id from $file..."
    curl -X PUT "$FHIR_URL/Patient/$id" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
    echo
  fi
done

# Load conditions
for file in sample-data/conditions/*.json; do
  if [ -f "$file" ]; then
    id="$(get_id_from_filename "$file")"
    echo "Loading condition with ID=$id from $file..."
    curl -X PUT "$FHIR_URL/Condition/$id" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
    echo
  fi
done

# Load medications
for file in sample-data/medications/*.json; do
  if [ -f "$file" ]; then
    id="$(get_id_from_filename "$file")"
    echo "Loading medication with ID=$id from $file..."
    curl -X PUT "$FHIR_URL/MedicationRequest/$id" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
    echo
  fi
done

# Load observations
for file in sample-data/observations/*.json; do
  if [ -f "$file" ]; then
    id="$(get_id_from_filename "$file")"
    echo "Loading observation with ID=$id from $file..."
    curl -X PUT "$FHIR_URL/Observation/$id" \
         -H "Content-Type: application/fhir+json" \
         -d @"$file"
    echo
  fi
done

echo "✅ Sample data loaded!"
