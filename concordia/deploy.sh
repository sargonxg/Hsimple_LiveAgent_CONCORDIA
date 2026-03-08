#!/usr/bin/env bash
# CONCORDIA — Deploy to Google Cloud Run
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-concordia}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== CONCORDIA Cloud Run Deployment ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Enable required APIs
echo ">>> Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

# Build container image
echo ">>> Building container image..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --project="${PROJECT_ID}" \
    --quiet

# Deploy to Cloud Run
echo ">>> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --timeout 3600 \
    --session-affinity \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
    --project="${PROJECT_ID}" \
    --quiet

# Output URL
URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --platform managed \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "URL: ${URL}"
echo ""
echo "Set your API key:"
echo "  curl -X POST ${URL}/api/set-key -H 'Content-Type: application/json' -d '{\"key\":\"YOUR_GEMINI_API_KEY\"}'"
