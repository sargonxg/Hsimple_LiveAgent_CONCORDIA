# CONCORDIA — Live AI Mediation Platform

Real-time AI-powered conflict mediation with knowledge graph visualization.
Powered by Google Gemini (ADK) · FastAPI · D3.js · Cloud Run.

## Repository Structure

```
├── concordia/          ← PRIMARY APP (ADK backend, deploy this to Cloud Run)
│   ├── main.py         ← FastAPI server + WebSocket streaming
│   ├── concordia_agent/← ADK agent with 17 tools + full ontology
│   ├── static/         ← Frontend SPA (landing → setup → mediation → resolution)
│   ├── requirements.txt
│   └── Dockerfile
│
├── main.py             ← Alternative simple backend (google-generativeai, no ADK)
├── agent.py            ← Simple Gemini agent
├── ontology.py         ← In-memory graph
├── theories.py         ← Theory matching
├── static/             ← Frontend for simple backend
└── Dockerfile          ← Docker for simple backend
```

## Deploy to Google Cloud Run (Primary — concordia/)

```bash
cd concordia

# Option A: Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT/concordia
gcloud run deploy concordia \
  --image gcr.io/YOUR_PROJECT/concordia \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_key_here \
  --port 8080 \
  --memory 1Gi

# Option B: Use deploy.sh
chmod +x deploy.sh
./deploy.sh
```

## Local Development

```bash
cd concordia
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set GOOGLE_API_KEY

uvicorn main:app --reload --port 8080
# → http://localhost:8080
```

## App Flow

1. **Landing** — CONCORDIA brand, optional API key entry
2. **Setup** — Case type (5), mediator style (3), party names
3. **Mediation** — Live chat + D3 knowledge graph + health intelligence
4. **Resolution** — AI-generated resolution paths, theories, export

## 8 Conflict Primitives

Actor · Claim · Interest · Constraint · Leverage · Commitment · Event · Narrative

## API Endpoints (concordia/)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health + API key status |
| GET | `/api/case-types` | Available case types |
| GET | `/api/styles` | Mediator styles |
| POST | `/api/set-key` | Set Gemini API key at runtime |
| POST | `/api/configure` | Set mediator_style + case_type |
| GET | `/api/graph` | Full knowledge graph |
| GET | `/api/theories` | Matched conflict theories |
| POST | `/api/upload` | Ingest document |
| POST | `/api/reset` | Reset session |
| WS | `/ws/{party}/{sid}` | Bidirectional streaming |
