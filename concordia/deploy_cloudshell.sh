#!/usr/bin/env bash
# ── CONCORDIA — Cloud Shell Quick Deploy ─────────────────────────────────────
# Run this in Google Cloud Shell for a one-command deployment.
# Opens at: https://shell.cloud.google.com
#
# Usage (paste in Cloud Shell):
#   GOOGLE_API_KEY="AIza..." bash deploy_cloudshell.sh
#
set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
SERVICE_NAME="concordia"

echo "Deploying CONCORDIA to project: ${PROJECT_ID}"

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com --quiet

# Build & Deploy in one command using Cloud Build + Cloud Run source deploy
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --allow-unauthenticated \
  --timeout 3600 \
  --session-affinity \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=FALSE,GOOGLE_API_KEY=${GOOGLE_API_KEY:-}" \
  --quiet

URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')
echo ""
echo "Done! Open: ${URL}"
echo "Health:     ${URL}/api/health"
