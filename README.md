# CONCORDIA — Live AI Mediation Platform

A real-time AI mediation system powered by Google Gemini, FastAPI, and D3.js. Deployed on Google Cloud Run.

## Architecture

- **Backend**: FastAPI + WebSockets (Python 3.11)
- **AI**: Google Gemini 2.0 Flash with function calling
- **Frontend**: Single-file SPA — D3.js force graph, 4-screen flow
- **Deploy**: Google Cloud Run (stateless, auto-scaling)

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export GEMINI_API_KEY=your_key_here

# Run
python main.py
# → http://localhost:8080
```

## Deploy to Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/concordia

# Deploy
gcloud run deploy concordia \
  --image gcr.io/YOUR_PROJECT/concordia \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here \
  --port 8080 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `PORT` | Server port | `8080` |

## App Flow

1. **Landing** → Brand intro, API key entry
2. **Setup** → Case type, mediator style, party names
3. **Mediation** → Live chat + D3 knowledge graph + intelligence panel
4. **Resolution** → Resolution paths, theories, export

## 8 Conflict Primitives

Actor · Claim · Interest · Constraint · Leverage · Commitment · Event · Narrative

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/case-types` | Available case types |
| GET | `/api/styles` | Mediator styles |
| POST | `/api/configure` | Update configuration |
| GET | `/api/graph` | Current knowledge graph |
| GET | `/api/theories` | Matched conflict theories |
| POST | `/api/upload` | Ingest document |
| POST | `/api/reset` | Reset session |
| WS | `/ws/{party}/{sid}` | Live mediation WebSocket |
