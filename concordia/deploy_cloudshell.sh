#!/usr/bin/env bash
# ── CONCORDIA — Google Cloud Shell One-Command Deploy ────────────────────────
#
# Paste this in Google Cloud Shell (https://shell.cloud.google.com):
#
#   GOOGLE_API_KEY="AIza..." bash deploy_cloudshell.sh
#
# Optional overrides:
#   REGION=europe-west1 SERVICE_NAME=concordia-demo GOOGLE_API_KEY="AIza..." bash deploy_cloudshell.sh
#   MODEL=gemini-2.0-flash-exp  # use text-only fallback (no Live API quota needed)
#
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-concordia}"
MODEL="${MODEL:-gemini-2.0-flash-live-001}"
VOICE="${VOICE:-Aoede}"
API_KEY="${GOOGLE_API_KEY:-}"

# ── Validation ────────────────────────────────────────────────────────────────
if [[ -z "$PROJECT_ID" ]]; then
  echo ""
  echo "ERROR: No GCP project configured."
  echo "Fix:   gcloud config set project YOUR_PROJECT_ID"
  echo "       or: PROJECT_ID=my-project bash deploy_cloudshell.sh"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     CONCORDIA — Cloud Shell Quick Deploy                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Project  : ${PROJECT_ID}"
echo "  Region   : ${REGION}"
echo "  Service  : ${SERVICE_NAME}"
echo "  Model    : ${MODEL}"
if [[ -n "$API_KEY" ]]; then
  echo "  API Key  : ${API_KEY:0:8}... (will be baked into service)"
else
  echo "  API Key  : NOT SET — set via UI after deploy or rerun with GOOGLE_API_KEY=..."
fi
echo ""

# ── Enable required GCP APIs ──────────────────────────────────────────────────
echo ">>> [1/3] Enabling Cloud Run + Cloud Build APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  --project="${PROJECT_ID}" \
  --quiet

# ── Build + Deploy (source deploy — no local Docker needed) ──────────────────
echo ">>> [2/3] Building and deploying from source (this takes ~3-5 min)..."

ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=FALSE,CONCORDIA_MODEL=${MODEL},CONCORDIA_VOICE=${VOICE}"
if [[ -n "$API_KEY" ]]; then
  ENV_VARS="${ENV_VARS},GOOGLE_API_KEY=${API_KEY}"
fi

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --timeout 3600 \
  --session-affinity \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "${ENV_VARS}" \
  --project="${PROJECT_ID}" \
  --quiet

# ── Output ────────────────────────────────────────────────────────────────────
URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)' 2>/dev/null || echo "")

echo ""
echo ">>> [3/3] Done!"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   DEPLOYMENT COMPLETE                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
if [[ -n "$URL" ]]; then
  echo "  App URL    : ${URL}"
  echo "  Health     : ${URL}/api/health"
  echo "  API Docs   : ${URL}/docs"
  echo "  Demo       : ${URL}  (click 'Demo' button — no API key needed)"
  echo ""
  if [[ -z "$API_KEY" ]]; then
    echo "  Set API key (run in Cloud Shell or browser console):"
    echo "    curl -X POST ${URL}/api/set-key \\"
    echo "      -H 'Content-Type: application/json' \\"
    echo "      -d '{\"key\":\"YOUR_GEMINI_API_KEY\"}'"
    echo ""
  fi
  echo "  Quick health check:"
  echo "    curl ${URL}/api/health"
  echo ""
  echo "  Fallback: to use text-only model (no Live API quota):"
  echo "    MODEL=gemini-2.0-flash-exp bash deploy_cloudshell.sh"
else
  echo "  Could not retrieve URL — run: gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
fi
echo ""
