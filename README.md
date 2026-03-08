# CONCORDIA — AI-Powered Conflict Mediation Agent

**CONCORDIA** is a real-time, conversational AI mediation system built on Google's Agent Development Kit (ADK) and Gemini Live API. It listens to each party in a dispute, silently builds a structured **conflict knowledge graph** (the TACITUS structure), identifies common ground, matches applicable resolution theories, and generates concrete **common ground proposals** — all through natural voice and text conversation.

---

## What CONCORDIA Does

```
Party 1 speaks ──► CONCORDIA listens ──► Extracts: actors, claims, interests,
Party 2 speaks ──► (silently)           constraints, leverage, commitments,
                                         events, narratives, edges
                                              │
                                              ▼
                                    TACITUS Conflict Graph
                                              │
                                              ▼
                                    Health Check (0-100%)
                                    Theory Matching (11 frameworks)
                                    Common Ground Analysis
                                              │
                                              ▼
                                    Resolution Proposals
                                    (ZOPA-grounded, party-specific)
```

Key properties:
- **Multi-party**: Each party speaks to the same agent separately; the agent builds a shared graph without revealing what the other party said
- **Real-time audio**: Powered by Gemini Live API (`gemini-2.0-flash-live-001`) — the agent speaks and listens in real time
- **Tool-augmented**: 17 ADK tools that Gemini calls silently during conversation to build the graph
- **Configurable**: 8 mediator styles × 5 case types × free-text objective = thousands of configurations
- **Deployable**: Local, Docker, Google Cloud Run, Google Cloud Shell

---

## Architecture

### Agent Hierarchy (Google ADK)

```
concordia (root)
  └── listener_agent
        └── verifier_agent
              └── resolver_agent
```

Each agent is a `google.adk.agents.Agent` with a distinct role:

| Agent | Role | Tools |
|-------|------|-------|
| `concordia` (root) | Welcomes parties, transfers immediately to listener | None |
| `listener_agent` | Natural conversation + silent graph building | 11 build tools |
| `verifier_agent` | Checks graph completeness, identifies gaps | 6 analysis tools |
| `resolver_agent` | Finds resolution paths, common ground proposals | 6 analysis tools |

The agents hand off using ADK's built-in `transfer_to_agent` mechanism — the graph is shared state in memory.

### The TACITUS Conflict Graph

CONCORDIA's knowledge structure is based on UN Security Council mediation practice, adapted for AI extraction. Every conflict is decomposed into 8 primitives:

| Primitive | Description | Example |
|-----------|-------------|---------|
| **Actor** | Person, org, state, group involved | "Maria Chen" (tenant) |
| **Claim** | Demand, accusation, grievance, proposal, justification | "Wants full deposit back" |
| **Interest** | Underlying need: security, economic, identity, autonomy, recognition, procedural | "Needs financial stability to cover next deposit" |
| **Constraint** | Legal, financial, temporal, normative, structural, relational limits | "30-day legal notice period" |
| **Leverage** | Coercive, reward, informational, normative, relational, structural power | "Landlord can withhold reference letter" |
| **Commitment** | Promises made (active, broken, fulfilled) | "Agreed to fix heating by November" |
| **Event** | Trigger, escalation, de-escalation, negotiation, agreement, violation | "Heating broke on Jan 5" |
| **Narrative** | How each party frames the conflict (victim, betrayal, injustice, etc.) | "Maria sees herself as exploited tenant" |
| **Edge** | Relationships between any two nodes | MAKES_CLAIM, HAS_INTEREST, HOLDS_LEVERAGE |

The graph is stored as a Pydantic `ConflictGraph` model in Python memory (per-session). Each node has a `contributed_by` field tracking which party provided it — enabling per-party health checks and confidentiality enforcement.

### Graph Health System

The health check evaluates 8 dimensions (0-100% score):
- Two or more actors identified
- All actors have claims
- All actors have interests
- Constraints identified
- Leverage mapped
- Events recorded
- Narratives captured
- Case metadata set (title + summary)

When score ≥ 75%, the agent transitions to resolution mode.

### Common Ground Analysis (find_common_ground)

The `find_common_ground()` method on `ConflictGraph`:
1. **Shared interests**: Groups interests by type; types held by 2+ actors = common ground
2. **Broken commitments**: Lists promises that were broken — acknowledgment needed before resolution
3. **Leverage balance**: Maps total leverage strength per actor; asymmetry flags need for safeguards

### Resolution Theory Matching

CONCORDIA scores 11 conflict resolution theories against the current graph:

| Theory | School | Best For |
|--------|--------|----------|
| Fisher & Ury — Interest-Based | Harvard Negotiation Project | Commercial, demand-heavy |
| Galtung Triangle | Peace Research (Transcend) | Deep-rooted, identity conflicts |
| Glasl 9-Stage Escalation | European conflict studies | Escalating disputes |
| Bush & Folger — Transformative | Relational/transformative | Relationship repair |
| Winslade & Monk — Narrative | Social constructionist | Identity, cultural conflicts |
| Interest-Based Relational | ADR / workplace | Workplace, ongoing partnerships |
| Principled Negotiation (ZOPA) | Negotiation theory | Multi-issue, commercial |
| Rights-Based Framework | Legal / human rights | Employment, contractual |
| Power Analysis | Critical conflict theory | Power-imbalanced disputes |
| Restorative Justice | Zehr / Pranis | Post-harm, trust violations |
| Peacemaking Circles | Indigenous / community | Community, multi-party harm |

Scoring is based on: matching claim types, matching interest types, escalation level, narrative frames, broken commitments count.

### WebSocket Protocol

The server exposes a bidi-streaming WebSocket at `/ws/{user_id}/{session_id}`.

**Incoming messages (client → server):**
```json
{ "type": "text", "content": "I want to discuss the rent dispute..." }
{ "type": "image", "data": "<base64>", "mime": "image/jpeg" }
```
Binary frames: raw PCM audio at 16kHz mono.

**Outgoing messages (server → client):**
```json
{ "type": "text", "content": "I hear you...", "author": "concordia" }
{ "type": "tool_call", "tool": "add_claim", "args": {...} }
{ "type": "graph_update", "graph": {...}, "health": {...}, "objective": "..." }
{ "type": "transcript", "content": "...", "role": "user|model" }
{ "type": "error", "content": "...", "error_type": "quota_exhausted|internal" }
```
Binary frames: PCM audio at 24kHz from the agent's voice.

---

## Mediator Styles (8)

Select at runtime — affects the agent's personality, questioning technique, and resolution philosophy:

| Style | Key Approach | Best For |
|-------|-------------|----------|
| **Empathetic Facilitator** | Emotional validation, reflective listening, slow pace | Family, personal disputes |
| **Analytical Strategist** | Systematic mapping, BATNA analysis, quantification | Commercial, workplace |
| **Directive Mediator** | Direct, efficient, reality-testing | Time-sensitive, high-stakes |
| **Transformative Mediator** | Empowerment + recognition moments (Bush & Folger) | Relationship repair |
| **Narrative Mediator** | Externalize problem, reauthor stories (Winslade & Monk) | Identity, cultural conflicts |
| **Facilitative Mediator** | Classic neutral process-manager, party-led solutions | Standard ADR |
| **Evaluative Mediator** | Assessments of merits, BATNA/WATNA, bracketing | Legal, rights-based |
| **Restorative Circle Facilitator** | Harm repair, accountability, community healing | Post-harm, justice contexts |

---

## Case Types (5)

Adjusts the ontology focus, probing questions, and applicable theories:

| Type | Focus | Probing Questions |
|------|-------|-------------------|
| **Workplace / HR** | Hierarchy, HR policies, power dynamics, documentation | Reporting relationship, paper trails, career impact |
| **Family / Relationship** | Emotional bonds, children, shared history, financial ties | Relationship history, dependents, shared values |
| **Commercial / Business** | Contracts, financial amounts, industry standards, ongoing relationship | Written agreement, dispute amounts, BATNA |
| **Community / Neighborhood** | Shared space, community norms, local regulations, long-term coexistence | Length of relationship, daily impact, bylaws |
| **Geopolitical / International** | Sovereignty, security, international law, historical grievances | Core territorial issues, security concerns, external actors |

---

## REST API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend UI |
| GET | `/api/health` | Server health + Gemini API status |
| GET | `/api/status` | Current mediation state summary |
| GET | `/api/graph` | Full conflict graph JSON |
| GET | `/api/common-ground` | Shared interests, broken commitments, leverage balance |
| GET | `/api/graph-summary` | Text summary of the graph (for display) |
| GET | `/api/theories` | Ranked applicable theories for current graph |
| GET | `/api/styles` | Available mediator styles |
| GET | `/api/case-types` | Available case types |
| GET | `/api/party-health/{party_id}` | Health check for one party's contributions |
| POST | `/api/set-key` | Set Gemini API key at runtime |
| POST | `/api/configure` | Set style + case type + objective, rebuild agents |
| POST | `/api/set-objective` | Update mediation objective only |
| POST | `/api/upload` | Upload a document (text) for ingestion |
| POST | `/api/reset` | Reset graph (optionally keep config) |
| WS | `/ws/{user_id}/{session_id}` | Bidi-streaming mediation session |

---

## Running Locally

### Option A: Python directly

```bash
cd concordia

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY

# Run
python main.py
# Or: uvicorn main:app --reload --port 8080

# Open http://localhost:8080
```

### Option B: Docker Compose

```bash
cd concordia

# Set your API key
export GOOGLE_API_KEY="AIzaSy..."

# Build and run
docker compose up --build

# Open http://localhost:8080
```

### Option C: Docker directly

```bash
cd concordia

docker build -t concordia .

docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="AIzaSy..." \
  -e CONCORDIA_MODEL="gemini-2.0-flash-live-001" \
  concordia

# Open http://localhost:8080
```

---

## Deploying to Google Cloud Run

Cloud Run is the recommended production deployment. It handles scaling, HTTPS, and WebSocket session affinity automatically.

### Prerequisites

```bash
# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Option A: deploy.sh (recommended)

```bash
cd concordia

# Set your API key
export GOOGLE_API_KEY="AIzaSy..."
export PROJECT_ID="your-gcp-project"

./deploy.sh
```

The script:
1. Enables required GCP APIs (Cloud Run, Cloud Build, Container Registry)
2. Builds the container image using Cloud Build
3. Deploys to Cloud Run with session affinity and 1-hour timeout
4. Prints the service URL

**Key Cloud Run flags explained:**
- `--session-affinity`: Routes WebSocket connections from the same client to the same instance (required for bidi-streaming)
- `--timeout 3600`: Allows 1-hour sessions (WebSocket connections are long-lived)
- `--memory 1Gi`: Each instance holds the conflict graph in memory
- `--min-instances 0`: Scales to zero when idle (cost-efficient)
- `--allow-unauthenticated`: Public access (add IAM auth for production)

### Option B: Google Cloud Shell (no local setup)

Open [Google Cloud Shell](https://shell.cloud.google.com), upload or clone the repo, then:

```bash
cd concordia
GOOGLE_API_KEY="AIzaSy..." bash deploy_cloudshell.sh
```

This uses `gcloud run deploy --source .` which builds and deploys in one command.

### Option C: Manual gcloud commands

```bash
cd concordia

PROJECT_ID="your-project"
REGION="us-central1"
IMAGE="gcr.io/${PROJECT_ID}/concordia"

# Build
gcloud builds submit --tag "${IMAGE}"

# Deploy
gcloud run deploy concordia \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --timeout 3600 \
  --session-affinity \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=FALSE,GOOGLE_API_KEY=YOUR_KEY,CONCORDIA_MODEL=gemini-2.0-flash-live-001"
```

### Post-Deployment: Set API Key Securely

For production, set the API key via Secret Manager instead of environment variables:

```bash
# Create secret
echo -n "AIzaSy..." | gcloud secrets create gemini-api-key --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:$(gcloud run services describe concordia --region us-central1 --format='value(spec.template.spec.serviceAccountName)')" \
  --role="roles/secretmanager.secretAccessor"

# Redeploy with secret
gcloud run deploy concordia \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --update-secrets="GOOGLE_API_KEY=gemini-api-key:latest"
```

### Monitoring & Logs

```bash
# View logs
gcloud run services logs read concordia --region us-central1

# Stream logs
gcloud run services logs tail concordia --region us-central1

# Check service status
gcloud run services describe concordia --region us-central1
```

---

## Using Vertex AI (instead of Google AI Studio)

To use Vertex AI instead of the public Gemini API:

1. Enable Vertex AI API: `gcloud services enable aiplatform.googleapis.com`
2. Update `.env`:
   ```env
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   # Remove GOOGLE_API_KEY (not needed for Vertex AI)
   ```
3. Cloud Run service account needs `roles/aiplatform.user` IAM role

---

## Using the App: Mediation Session Guide

### 1. Configure
- Set your Gemini API key (top-left input or via `/api/set-key`)
- Choose a **Mediator Style** that fits the dispute:
  - Family conflict → Empathetic or Transformative
  - Business dispute → Analytical or Evaluative
  - Community issue → Facilitative or Restorative Circle
  - Rights violation → Evaluative or Rights-Based
- Choose a **Case Type** (workplace, family, commercial, community, geopolitical)
- Enter a **Mediation Objective** (optional but recommended)
  - Example: "Reach agreement on lease termination terms by end of month"
  - Example: "Establish a co-parenting schedule that prioritizes the children's needs"

### 2. Party 1 Session
- Set party to "Party 1", click Connect
- Party 1 speaks naturally — the agent listens and builds the graph silently
- Watch the graph stats update as data is extracted
- The health bar shows readiness for resolution (75% threshold)
- Document upload: drag-drop a contract, email, or letter for automatic extraction

### 3. Party 2 Session
- Change party to "Party 2", click Connect (creates a new session)
- Party 2 speaks independently — the agent says "I have some background" but reveals nothing from Party 1
- The agent uses the same graph, adding Party 2's perspective

### 4. Analysis
- **Graph tab**: Visual network of actors, claims, interests and their relationships
- **Theories tab**: Auto-ranked applicable conflict resolution frameworks
- **Resolve tab**: Click "Analyze Common Ground" to see shared interests, broken commitments, and leverage balance

### 5. Resolution
- When graph health ≥ 75%, the agent transfers to `resolver_agent`
- The resolver proposes 2-3 concrete resolution paths grounded in graph data
- Each path includes: what each side gets/gives, why it works, risks, and implementation steps
- The "Ask Agent for Resolution Paths" button in the Resolve tab triggers this directly

### Tips for Best Results
- **Let the agent drive**: It knows when to probe for more information
- **Be specific**: "They fired me on January 5 with no warning" extracts better data than "it was unfair"
- **Upload documents**: Contracts, emails, letters — the agent extracts all primitives automatically
- **Use voice mode**: The Gemini Live API enables natural back-and-forth — the agent handles interruptions
- **Switch styles mid-session**: If analytical isn't working, switch to empathetic without losing data

---

## Project Structure

```
concordia/
├── main.py                          # FastAPI server, WebSocket, REST endpoints
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Production container
├── docker-compose.yml               # Local development
├── deploy.sh                        # Cloud Run deployment script
├── deploy_cloudshell.sh             # Google Cloud Shell one-liner
├── .env.example                     # Environment variable template
├── .gitignore
├── static/
│   └── index.html                   # Full-featured frontend UI
└── concordia_agent/
    ├── __init__.py                  # Exports: root_agent, graph, build_agents
    ├── agent.py                     # Agent factory (listener/verifier/resolver hierarchy)
    ├── ontology.py                  # ConflictGraph + 8 primitives + health check
    ├── tools.py                     # 17 ADK tool functions
    ├── styles.py                    # 8 mediator style configurations
    ├── case_types.py                # 5 case type configurations
    └── resolution_library.py       # 11 conflict resolution theories
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Gemini API key from Google AI Studio |
| `GOOGLE_GENAI_USE_VERTEXAI` | `FALSE` | Set `TRUE` to use Vertex AI instead |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID (Vertex AI only) |
| `GOOGLE_CLOUD_LOCATION` | — | GCP region (Vertex AI only) |
| `CONCORDIA_MODEL` | `gemini-2.0-flash-live-001` | Gemini model to use |
| `CONCORDIA_VOICE` | `Aoede` | Voice for audio output |
| `PORT` | `8080` | Server port (Cloud Run injects this) |

**Available voices**: Aoede, Charon, Fenrir, Kore, Puck, Orbit, Zephyr

**Available models**:
- `gemini-2.0-flash-live-001` — Real-time audio + text (recommended)
- `gemini-2.0-flash-exp` — Text only (fallback, lower latency for text)

---

## Extending CONCORDIA

### Add a New Mediator Style

In `concordia_agent/styles.py`, add an entry to `MEDIATOR_STYLES`:

```python
"my_style": {
    "name": "My Custom Style",
    "icon": "🎯",
    "description": "Description of when to use this style.",
    "instruction_modifier": """
STYLE: MY CUSTOM STYLE
- Your behavioral instructions here...
- How to open conversations
- What to prioritize
- How to summarize
""",
},
```

### Add a New Case Type

In `concordia_agent/case_types.py`:

```python
"healthcare": {
    "name": "Healthcare / Patient Dispute",
    "icon": "🏥",
    "description": "Medical negligence, patient rights, provider disputes",
    "focus_interests": ["security", "autonomy", "procedural"],
    "focus_claims": ["accusation", "grievance", "demand"],
    "context_prompt": """This is a HEALTHCARE dispute. Focus on:
- Patient rights and informed consent
- Medical standards of care
...
""",
    "probing_questions": [
        "What treatment decision is at the center of this dispute?",
        ...
    ],
},
```

### Add a New Resolution Theory

In `concordia_agent/resolution_library.py`:

```python
"my_theory": {
    "name": "My Theory Name",
    "short": "Tagline",
    "school": "Academic school",
    "principles": ["Principle 1", "Principle 2"],
    "best_for": ["conflict type 1", "conflict type 2"],
    "techniques": ["Technique 1", "Technique 2"],
    "indicators": {
        "claim_types": ["demand", "grievance"],   # Boosts score when present
        "interest_types": ["economic"],
        "escalation_min": "emerging",             # Minimum escalation level
        "has_broken_commitments": True,           # Requires broken commitments
        "min_narratives": 2,                      # Minimum narratives in graph
    },
},
```

### Add a New Tool

In `concordia_agent/tools.py`:

```python
def my_new_tool(arg1: str, arg2: int) -> dict:
    """Tool description — Gemini uses this docstring to understand when to call it.
    
    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.
    
    Returns:
        dict with the result.
    """
    graph = _graph()
    # Do something with the graph
    return {"status": "ok"}
```

Then add it to the appropriate tool list:
```python
LISTENER_TOOLS = [..., my_new_tool]
ANALYZER_TOOLS = [..., my_new_tool]
```

---

## Troubleshooting

### "no_api_key" in health check
Set your Gemini API key: `POST /api/set-key {"key": "AIzaSy..."}`

### WebSocket won't connect
- Check that the server is running: `GET /api/health`
- For Cloud Run: ensure `--session-affinity` flag is set
- For Cloud Run: ensure `--timeout 3600` is set (default is 300s, too short for WebSocket sessions)

### Agent doesn't respond
- Check logs for Gemini API errors
- Try text-only model: set `CONCORDIA_MODEL=gemini-2.0-flash-exp` 
- Check quota: Gemini Live API has separate quotas from standard Gemini

### Audio not working
- Audio requires HTTPS in production (or `localhost` for development)
- The model must support audio: only `*-live-*` and `*-native-audio-*` models do
- Check browser microphone permissions

### Graph not updating
- The graph updates happen on tool calls — check the chat for tool call pills (purple ⚙ labels)
- If no tool calls appear, the agent may not be recognizing extraction triggers — try being more specific in your messages

---

## License

MIT License — See LICENSE file.

Built with:
- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [Google Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic v2](https://docs.pydantic.dev/)
