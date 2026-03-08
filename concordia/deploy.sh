#!/usr/bin/env bash
# ── CONCORDIA — Deploy to Google Cloud Run ───────────────────────────────────
# Usage:
#   ./deploy.sh                          # Use gcloud defaults
#   PROJECT_ID=my-project ./deploy.sh    # Override project
#   SERVICE_NAME=concordia-prod ./deploy.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Docker installed (for local builds) OR gcloud builds available
#   - GOOGLE_API_KEY set in environment or passed as GEMINI_KEY=...
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-concordia}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
GEMINI_KEY="${GEMINI_KEY:-${GOOGLE_API_KEY:-}}"
CONCORDIA_MODEL="${CONCORDIA_MODEL:-gemini-2.0-flash-live-001}"
CONCORDIA_VOICE="${CONCORDIA_VOICE:-Aoede}"

# ── Validation ────────────────────────────────────────────────────────────────
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        CONCORDIA — Google Cloud Run Deployment           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Service : ${SERVICE_NAME}"
echo "  Image   : ${IMAGE}"
echo "  Model   : ${CONCORDIA_MODEL}"
echo "  API Key : ${GEMINI_KEY:0:8}... (${#GEMINI_KEY} chars)"
echo ""

if [[ -z "$GEMINI_KEY" ]]; then
  echo "WARNING: GOOGLE_API_KEY not set. You'll need to set it via the UI or POST /api/set-key"
fi

# ── Enable APIs ───────────────────────────────────────────────────────────────
echo ">>> [1/4] Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

# ── Build Container ───────────────────────────────────────────────────────────
echo ">>> [2/4] Building container image with Cloud Build..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --project="${PROJECT_ID}" \
    --quiet

# ── Deploy ────────────────────────────────────────────────────────────────────
echo ">>> [3/4] Deploying to Cloud Run..."

ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=FALSE,CONCORDIA_MODEL=${CONCORDIA_MODEL},CONCORDIA_VOICE=${CONCORDIA_VOICE}"
if [[ -n "$GEMINI_KEY" ]]; then
  ENV_VARS="${ENV_VARS},GOOGLE_API_KEY=${GEMINI_KEY}"
fi

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
    --set-env-vars "${ENV_VARS}" \
    --project="${PROJECT_ID}" \
    --quiet

# ── Output ────────────────────────────────────────────────────────────────────
URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --platform managed \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')

echo ""
echo ">>> [4/4] Deployment complete!"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   DEPLOYMENT COMPLETE                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  App URL  : ${URL}"
echo "  Health   : ${URL}/api/health"
echo "  API Docs : ${URL}/docs"
echo ""

if [[ -z "$GEMINI_KEY" ]]; then
  echo "  Set API key:"
  echo "  curl -X POST ${URL}/api/set-key \\"
  echo "    -H 'Content-Type: application/json' \\"
  echo "    -d '{\"key\":\"YOUR_GEMINI_API_KEY\"}'"
  echo ""
fi

echo "  Quick test:"
echo "  curl ${URL}/api/health"
echo ""
