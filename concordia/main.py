"""
CONCORDIA — FastAPI Bidi-Streaming Server

Multi-party mediation server with:
  - WebSocket bidi-streaming for real-time mediation (ADK Live API)
  - REST API for graph state, health, configuration, document upload
  - Runtime agent reconfiguration (mediator style + case type + objective)
  - Session tracking with per-party awareness
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Load .env BEFORE importing agent so CONCORDIA_MODEL is available
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel as PydanticBaseModel, Field

from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from concordia_agent import root_agent, graph, build_agents
import concordia_agent.ontology as ontology

# ── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("concordia")


# ── Application Initialization ───────────────────────────────────────────────

APP_NAME = "concordia"

app = FastAPI(title="CONCORDIA — Live AI Mediation Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

# Current mediation objective (shared across all parties in this session)
_current_objective: str = ""


# ── Request/Response Models ──────────────────────────────────────────────────

class ApiKeyRequest(PydanticBaseModel):
    key: str


class UploadDocumentRequest(PydanticBaseModel):
    party_id: str = "party1"
    text: str
    document_name: str = "Uploaded Document"


class ConfigureRequest(PydanticBaseModel):
    mediator_style: str = "empathetic"
    case_type: str = "workplace"
    objective: str = ""


class ObjectiveRequest(PydanticBaseModel):
    objective: str


class ResetRequest(PydanticBaseModel):
    keep_config: bool = False


# ── REST Endpoints — Graph & Health ──────────────────────────────────────────

@app.get("/api/graph")
async def api_get_graph():
    """Return the full conflict graph as JSON."""
    data = json.loads(graph.model_dump_json())
    data["health"] = graph.health_check()
    return data


@app.get("/api/health")
async def api_get_health():
    """Health check — includes Gemini API connectivity status."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    gemini_status = "configured" if api_key else "no_api_key"
    return {
        "status": "healthy",
        "gemini_api": gemini_status,
        "graph_health": graph.health_check(),
    }


@app.get("/api/status")
async def api_get_status():
    """Return a summary of the current mediation state."""
    return {
        "title": graph.case_title,
        "phase": graph.phase,
        "parties": graph.parties,
        "objective": _current_objective,
        "counts": {
            "actors": len(graph.actors),
            "claims": len(graph.claims),
            "interests": len(graph.interests),
            "constraints": len(graph.constraints),
            "leverages": len(graph.leverages),
            "commitments": len(graph.commitments),
            "events": len(graph.events),
            "narratives": len(graph.narratives),
            "edges": len(graph.edges),
            "documents": len(graph.documents),
        },
        "health": graph.health_check(),
    }


@app.get("/api/party-health/{party_id}")
async def api_party_health(party_id: str):
    """Return health check for a specific party's contributions."""
    return graph.per_party_health_check(party_id)


# ── REST Endpoints — Configuration ──────────────────────────────────────────

@app.post("/api/set-key")
async def set_api_key(req: ApiKeyRequest):
    """Set the Gemini API key at runtime (demo only)."""
    os.environ["GOOGLE_API_KEY"] = req.key
    logger.info("API key updated at runtime.")
    return {"status": "ok"}


@app.post("/api/configure")
async def configure(req: ConfigureRequest):
    """Reconfigure mediator style, case type, and objective. Rebuilds agent hierarchy."""
    global _current_objective
    import concordia_agent
    _current_objective = req.objective
    new_root = build_agents(req.mediator_style, req.case_type, req.objective)
    concordia_agent.root_agent = new_root
    global runner
    runner = Runner(app_name=APP_NAME, agent=new_root, session_service=session_service)
    logger.info(f"Reconfigured: style={req.mediator_style}, case_type={req.case_type}, objective_len={len(req.objective)}")
    return {
        "status": "configured",
        "mediator_style": req.mediator_style,
        "case_type": req.case_type,
        "objective": req.objective,
    }


@app.post("/api/set-objective")
async def set_objective(req: ObjectiveRequest):
    """Update the mediation objective and rebuild agents (keeps current style/case type)."""
    global _current_objective
    _current_objective = req.objective
    import concordia_agent
    # Rebuild with current style/case type + new objective
    # We keep the same model config but update objective
    new_root = build_agents(
        os.getenv("CONCORDIA_STYLE", "empathetic"),
        os.getenv("CONCORDIA_CASE_TYPE", "workplace"),
        req.objective,
    )
    concordia_agent.root_agent = new_root
    global runner
    runner = Runner(app_name=APP_NAME, agent=new_root, session_service=session_service)
    logger.info(f"Objective updated: {req.objective[:80]}")
    return {"status": "ok", "objective": req.objective}


@app.get("/api/styles")
async def get_styles():
    """Get available mediator styles."""
    from concordia_agent.styles import get_all_styles
    return get_all_styles()


@app.get("/api/case-types")
async def get_case_types():
    """Get available case type configurations."""
    from concordia_agent.case_types import get_all_case_types
    return get_all_case_types()


@app.get("/api/theories")
async def get_theories():
    """Get applicable conflict resolution theories for current graph."""
    from concordia_agent.resolution_library import get_applicable_theories
    return get_applicable_theories(ontology.graph)


@app.get("/api/common-ground")
async def api_common_ground():
    """Return common ground analysis: shared interests, broken commitments, leverage balance."""
    return ontology.graph.find_common_ground()


@app.get("/api/graph-summary")
async def api_graph_summary():
    """Return a concise text summary of the conflict graph for display."""
    return {"summary": ontology.graph.graph_summary_for_agent()}


# ── REST Endpoints — Document Upload & Reset ─────────────────────────────────

@app.post("/api/upload")
async def upload_document(req: UploadDocumentRequest):
    """Upload a text document for ingestion into the conflict graph."""
    from concordia_agent.tools import ingest_document
    ontology.active_party = req.party_id
    result = ingest_document(text=req.text, name=req.document_name)
    logger.info(f"Document uploaded: {req.document_name} ({len(req.text)} chars) by {req.party_id}")
    return result


@app.post("/api/reset")
async def reset_graph(req: ResetRequest = ResetRequest()):
    """Reset the conflict graph to empty state."""
    global _current_objective
    from concordia_agent.ontology import ConflictGraph
    ontology.graph = ConflictGraph()
    ontology.active_party = "default"
    import concordia_agent
    concordia_agent.graph = ontology.graph
    if not req.keep_config:
        _current_objective = ""
    logger.info("Graph reset.")
    return {"status": "reset"}


@app.post("/api/load-demo")
async def load_demo():
    """Load a pre-built demo conflict scenario (Maria Chen vs. Greenfield Properties lease dispute).

    Populates the conflict graph with a complete, realistic landlord-tenant dispute
    including actors, claims, interests, constraints, leverage, events, commitments,
    and narratives — enabling all app features without a live Gemini API session.
    """
    from concordia_agent.ontology import (
        ConflictGraph, Actor, ActorType, Claim, ClaimType,
        Interest, InterestType, Constraint, ConstraintType,
        Leverage, LeverageType, Commitment, CommitmentStatus,
        Event, EventType, Narrative, Edge, EscalationLevel, Phase,
    )

    g = ConflictGraph()
    g.case_title = "Chen v. Greenfield Properties — Lease Termination & Deposit Dispute"
    g.case_summary = (
        "Maria Chen, a software engineer, is in dispute with her landlord David Park "
        "(representing Greenfield Properties) over the wrongful withholding of a $3,200 "
        "security deposit and the circumstances of her lease termination. Maria alleges the "
        "apartment had undisclosed heating defects and that the eviction notice was retaliatory "
        "after she filed an official maintenance complaint. David claims the deposit covers "
        "cleaning and minor damage beyond normal wear, and that the termination was valid under "
        "clause 14 of the lease agreement."
    )
    g.escalation_level = EscalationLevel.ESCALATING
    g.phase = Phase.STRUCTURE
    g.parties = ["party1", "party2"]

    # ── Actors ────────────────────────────────────────────────────────────────
    maria = Actor(
        name="Maria Chen",
        actor_type=ActorType.INDIVIDUAL,
        description="Software engineer, former tenant of 4B Lakeview Apartments",
        role_in_conflict="Complainant / former tenant",
        contributed_by="party1",
    )
    david = Actor(
        name="David Park",
        actor_type=ActorType.INDIVIDUAL,
        description="Property manager for Greenfield Properties",
        role_in_conflict="Respondent / landlord representative",
        contributed_by="party2",
    )
    greenfield = Actor(
        name="Greenfield Properties",
        actor_type=ActorType.ORGANIZATION,
        description="Residential property management company, owns 4B Lakeview",
        role_in_conflict="Organizational defendant",
        contributed_by="party2",
    )
    g.actors.extend([maria, david, greenfield])

    # ── Claims ────────────────────────────────────────────────────────────────
    c1 = Claim(claim_type=ClaimType.DEMAND, content="Return $3,200 security deposit in full",
               source_actor_id=maria.id, target_actor_id=david.id, contributed_by="party1")
    c2 = Claim(claim_type=ClaimType.ACCUSATION, content="Retaliatory eviction: notice issued 6 days after formal maintenance complaint",
               source_actor_id=maria.id, target_actor_id=david.id, contributed_by="party1")
    c3 = Claim(claim_type=ClaimType.GRIEVANCE, content="Heating system was broken for 47 days — never disclosed at move-in",
               source_actor_id=maria.id, target_actor_id=greenfield.id, contributed_by="party1")
    c4 = Claim(claim_type=ClaimType.JUSTIFICATION, content="Deposit withheld per lease clause 8: cleaning costs $890, carpet damage $680",
               source_actor_id=david.id, target_actor_id=maria.id, contributed_by="party2")
    c5 = Claim(claim_type=ClaimType.JUSTIFICATION, content="Termination issued under clause 14 (repeated late rent). First late payment in 22 months triggered a valid notice",
               source_actor_id=david.id, target_actor_id=maria.id, contributed_by="party2")
    c6 = Claim(claim_type=ClaimType.PROPOSAL, content="Willing to return 50% of deposit ($1,600) if Maria drops the retaliation claim",
               source_actor_id=david.id, target_actor_id=maria.id, contributed_by="party2")
    g.claims.extend([c1, c2, c3, c4, c5, c6])

    # ── Interests ─────────────────────────────────────────────────────────────
    i1 = Interest(interest_type=InterestType.ECONOMIC, description="Needs deposit to cover first/last month rent for new apartment",
                  actor_id=maria.id, priority=5, contributed_by="party1")
    i2 = Interest(interest_type=InterestType.RECOGNITION, description="Wants acknowledgment that maintenance was neglected and eviction was unfair",
                  actor_id=maria.id, priority=4, contributed_by="party1")
    i3 = Interest(interest_type=InterestType.SECURITY, description="Concerned about rental history record and ability to secure future housing",
                  actor_id=maria.id, priority=4, contributed_by="party1")
    i4 = Interest(interest_type=InterestType.ECONOMIC, description="Minimize financial exposure: avoid litigation costs and precedent for other tenants",
                  actor_id=david.id, priority=5, contributed_by="party2")
    i5 = Interest(interest_type=InterestType.PROCEDURAL, description="Establish that lease clauses are enforceable to protect future tenancy management",
                  actor_id=david.id, priority=4, contributed_by="party2")
    i6 = Interest(interest_type=InterestType.SECURITY, description="Protect company reputation — avoid public record of retaliation judgment",
                  actor_id=greenfield.id, priority=5, contributed_by="party2")
    g.interests.extend([i1, i2, i3, i4, i5, i6])

    # ── Constraints ───────────────────────────────────────────────────────────
    con1 = Constraint(constraint_type=ConstraintType.LEGAL, description="State landlord-tenant law: deposits must be returned within 21 days with itemized deductions",
                      affects_actor_ids=[david.id, greenfield.id], contributed_by="party1")
    con2 = Constraint(constraint_type=ConstraintType.FINANCIAL, description="Maria's new apartment deposit due in 12 days — cash flow critical",
                      affects_actor_ids=[maria.id], contributed_by="party1")
    con3 = Constraint(constraint_type=ConstraintType.TEMPORAL, description="Small claims court filing deadline: 30 days from deposit withholding notice",
                      affects_actor_ids=[maria.id], contributed_by="party1")
    con4 = Constraint(constraint_type=ConstraintType.LEGAL, description="Anti-retaliation statute: eviction within 90 days of maintenance complaint creates presumption of retaliation",
                      affects_actor_ids=[david.id, greenfield.id], contributed_by="party1")
    con5 = Constraint(constraint_type=ConstraintType.STRUCTURAL, description="Greenfield Properties manages 340 units — retaliation precedent threatens business model",
                      affects_actor_ids=[greenfield.id], contributed_by="party2")
    g.constraints.extend([con1, con2, con3, con4, con5])

    # ── Leverage ──────────────────────────────────────────────────────────────
    l1 = Leverage(leverage_type=LeverageType.COERCIVE, description="Maria can file in small claims court for 3x deposit damages under retaliation statute",
                  held_by_actor_id=maria.id, target_actor_id=greenfield.id, strength=4, contributed_by="party1")
    l2 = Leverage(leverage_type=LeverageType.INFORMATIONAL, description="Maria has documented heating complaints with timestamps and photos",
                  held_by_actor_id=maria.id, target_actor_id=david.id, strength=4, contributed_by="party1")
    l3 = Leverage(leverage_type=LeverageType.STRUCTURAL, description="Greenfield can issue negative rental reference, affecting Maria's ability to rent elsewhere",
                  held_by_actor_id=greenfield.id, target_actor_id=maria.id, strength=3, contributed_by="party2")
    l4 = Leverage(leverage_type=LeverageType.NORMATIVE, description="Lease clause 14 gives procedural cover for termination regardless of motive",
                  held_by_actor_id=david.id, target_actor_id=maria.id, strength=3, contributed_by="party2")
    g.leverages.extend([l1, l2, l3, l4])

    # ── Commitments ───────────────────────────────────────────────────────────
    k1 = Commitment(description="Greenfield promised in writing to fix heating system by November 15",
                    committed_actor_id=greenfield.id, to_actor_id=maria.id,
                    status=CommitmentStatus.BROKEN, contributed_by="party1")
    k2 = Commitment(description="Maria agreed to clean the apartment to 'move-in condition' per lease clause 7",
                    committed_actor_id=maria.id, to_actor_id=greenfield.id,
                    status=CommitmentStatus.FULFILLED, contributed_by="party2")
    g.commitments.extend([k1, k2])

    # ── Events ────────────────────────────────────────────────────────────────
    e1 = Event(event_type=EventType.TRIGGER, description="Heating system failed during cold snap; Maria reported issue to maintenance portal",
               date="2024-11-01", involved_actor_ids=[maria.id, greenfield.id], contributed_by="party1")
    e2 = Event(event_type=EventType.ESCALATION, description="After 47 days without repair, Maria filed formal complaint with City Housing Authority",
               date="2024-12-18", involved_actor_ids=[maria.id, greenfield.id], contributed_by="party1")
    e3 = Event(event_type=EventType.ESCALATION, description="David issued 30-day termination notice citing clause 14 (one day of late rent, Dec 1)",
               date="2024-12-24", involved_actor_ids=[david.id, maria.id], contributed_by="party2")
    e4 = Event(event_type=EventType.NEGOTIATION, description="Maria requested mediation in lieu of small claims court; David agreed",
               date="2025-01-10", involved_actor_ids=[maria.id, david.id], contributed_by="party1")
    e5 = Event(event_type=EventType.VIOLATION, description="Deposit not returned within statutory 21-day window; no itemized deduction letter provided",
               date="2025-01-14", involved_actor_ids=[greenfield.id, maria.id], contributed_by="party1")
    g.events.extend([e1, e2, e3, e4, e5])

    # ── Narratives ────────────────────────────────────────────────────────────
    n1 = Narrative(description="Maria sees herself as a responsible tenant who maintained the unit, paid rent on time for 22 months, and was evicted as punishment for exercising her legal right to complain",
                   held_by_actor_id=maria.id, frames=["victim", "retaliation", "injustice", "rights_violation"],
                   contributed_by="party1")
    n2 = Narrative(description="David sees Maria as a difficult tenant who left the unit in poor condition and is exploiting a technicality to avoid responsibility for legitimate cleaning charges",
                   held_by_actor_id=david.id, frames=["opportunism", "system_abuse", "entitlement"],
                   contributed_by="party2")
    g.narratives.extend([n1, n2])

    # ── Edges ─────────────────────────────────────────────────────────────────
    for claim in [c1, c2, c3]:
        g.edges.append(Edge(source_id=maria.id, target_id=claim.id, relationship="MAKES_CLAIM",
                            description=f"Maria makes {claim.claim_type}"))
        if claim.target_actor_id:
            g.edges.append(Edge(source_id=claim.id, target_id=claim.target_actor_id,
                                relationship="CLAIM_TARGETS", description="Claim targets"))
    for claim in [c4, c5, c6]:
        g.edges.append(Edge(source_id=david.id, target_id=claim.id, relationship="MAKES_CLAIM",
                            description=f"David makes {claim.claim_type}"))
        g.edges.append(Edge(source_id=claim.id, target_id=maria.id, relationship="CLAIM_TARGETS",
                            description="Claim targets Maria"))
    for interest in [i1, i2, i3]:
        g.edges.append(Edge(source_id=maria.id, target_id=interest.id, relationship="HAS_INTEREST",
                            description=f"Maria: {interest.interest_type}"))
    for interest in [i4, i5]:
        g.edges.append(Edge(source_id=david.id, target_id=interest.id, relationship="HAS_INTEREST",
                            description=f"David: {interest.interest_type}"))
    g.edges.append(Edge(source_id=greenfield.id, target_id=i6.id, relationship="HAS_INTEREST",
                        description="Greenfield: security interest"))
    for lev in [l1, l2]:
        g.edges.append(Edge(source_id=maria.id, target_id=lev.id, relationship="HOLDS_LEVERAGE",
                            description=f"Maria holds {lev.leverage_type} leverage"))
    for lev in [l3, l4]:
        g.edges.append(Edge(source_id=greenfield.id if lev == l3 else david.id, target_id=lev.id,
                            relationship="HOLDS_LEVERAGE", description=f"Holds {lev.leverage_type}"))
    g.edges.append(Edge(source_id=maria.id, target_id=n1.id, relationship="HOLDS_NARRATIVE",
                        description="Maria's narrative"))
    g.edges.append(Edge(source_id=david.id, target_id=n2.id, relationship="HOLDS_NARRATIVE",
                        description="David's narrative"))
    g.edges.append(Edge(source_id=greenfield.id, target_id=david.id, relationship="EMPLOYS",
                        description="Greenfield employs David as property manager"))
    g.edges.append(Edge(source_id=k1.id, target_id=maria.id, relationship="BROKEN_COMMITMENT_AFFECTS",
                        description="Broken heating promise affects Maria"))

    # Install demo graph as the active graph
    ontology.graph = g
    import concordia_agent
    concordia_agent.graph = g

    health = g.health_check()
    common = g.find_common_ground()
    logger.info("Demo scenario loaded: Chen v. Greenfield Properties")
    return {
        "status": "loaded",
        "case_title": g.case_title,
        "health": health,
        "counts": {
            "actors": len(g.actors),
            "claims": len(g.claims),
            "interests": len(g.interests),
            "constraints": len(g.constraints),
            "leverages": len(g.leverages),
            "commitments": len(g.commitments),
            "events": len(g.events),
            "narratives": len(g.narratives),
            "edges": len(g.edges),
        },
        "shared_interests_count": len(common["shared_interests"]),
        "broken_commitments_count": len(common["broken_commitments"]),
    }


# ── WebSocket Helpers ────────────────────────────────────────────────────────

def _build_run_config() -> RunConfig:
    """Build RunConfig based on model capabilities."""
    model_name = os.getenv("CONCORDIA_MODEL", "gemini-2.0-flash-live-001")
    voice_name = os.getenv("CONCORDIA_VOICE", "Aoede")

    if "live" in model_name or "native-audio" in model_name:
        return RunConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
            streaming_mode=StreamingMode.BIDI,
        )
    return RunConfig(
        response_modalities=["TEXT"],
        session_resumption=types.SessionResumptionConfig(),
        streaming_mode=StreamingMode.BIDI,
    )


# ── WebSocket Endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """Bidi-streaming WebSocket for real-time mediation via ADK Live API."""
    await websocket.accept()
    logger.info(f"WebSocket connected: user={user_id}, session={session_id}")

    # Set active party
    ontology.active_party = user_id
    if user_id not in graph.parties:
        graph.parties.append(user_id)

    run_config = _build_run_config()
    live_request_queue = LiveRequestQueue()

    # Get or create session
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    # Send initial graph state and objective
    try:
        await websocket.send_json({
            "type": "graph_update",
            "graph": json.loads(graph.model_dump_json()),
            "health": graph.health_check(),
            "objective": _current_objective,
        })
    except Exception:
        pass

    async def upstream_task():
        """Client -> LiveRequestQueue: forward text, images, and audio."""
        try:
            while True:
                data = await websocket.receive()

                if "text" in data:
                    try:
                        msg = json.loads(data["text"])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from {user_id}")
                        continue

                    if msg.get("type") == "text":
                        ontology.active_party = user_id
                        content = types.Content(
                            role="user",
                            parts=[types.Part(text=msg["content"])],
                        )
                        live_request_queue.send_content(content)

                    elif msg.get("type") == "image":
                        image_bytes = base64.b64decode(msg["data"])
                        live_request_queue.send_realtime(
                            types.Blob(
                                data=image_bytes,
                                mime_type=msg.get("mime", "image/jpeg"),
                            )
                        )

                elif "bytes" in data:
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data["bytes"],
                            mime_type="audio/pcm;rate=16000",
                        )
                    )

        except WebSocketDisconnect:
            logger.info(f"Client disconnected (upstream): {user_id}")
        except Exception as e:
            logger.error(f"Upstream error for {user_id}: {e}")

    async def downstream_task():
        """run_live() events -> Client: forward text, audio, tool calls, graph updates."""
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                if not event.content or not event.content.parts:
                    continue

                for part in event.content.parts:
                    # Text response
                    if hasattr(part, "text") and part.text:
                        try:
                            await websocket.send_json({
                                "type": "text",
                                "content": part.text,
                                "author": event.author or "concordia",
                            })
                        except Exception:
                            return

                    # Audio response
                    if hasattr(part, "inline_data") and part.inline_data:
                        if "audio" in (part.inline_data.mime_type or ""):
                            try:
                                await websocket.send_bytes(part.inline_data.data)
                            except Exception:
                                return

                    # Tool call -> send tool info AND updated graph
                    if hasattr(part, "function_call") and part.function_call:
                        try:
                            await websocket.send_json({
                                "type": "tool_call",
                                "tool": part.function_call.name,
                                "args": dict(part.function_call.args) if part.function_call.args else {},
                            })
                            graph_data = json.loads(graph.model_dump_json())
                            health = graph.health_check()
                            await websocket.send_json({
                                "type": "graph_update",
                                "graph": graph_data,
                                "health": health,
                                "objective": _current_objective,
                            })
                        except Exception as e:
                            logger.error(f"Error sending tool update: {e}")
                            return

                    # Transcript (from audio transcription)
                    if hasattr(part, "transcript") and part.transcript:
                        try:
                            await websocket.send_json({
                                "type": "transcript",
                                "content": part.transcript,
                                "role": event.content.role or "model",
                            })
                        except Exception:
                            pass

        except WebSocketDisconnect:
            logger.info(f"Client disconnected (downstream): {user_id}")
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "resource_exhausted" in error_msg:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "content": "The AI service is temporarily at capacity. Please wait a moment and try again.",
                        "error_type": "quota_exhausted",
                    })
                except Exception:
                    pass
            else:
                logger.error(f"Downstream error for {user_id}: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "content": "An unexpected error occurred. Your data is saved — please reconnect.",
                        "error_type": "internal",
                    })
                except Exception:
                    pass

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except Exception as e:
        logger.error(f"Session error for {user_id}: {e}")
    finally:
        live_request_queue.close()
        logger.info(f"Session closed: user={user_id}, session={session_id}")


# ── Static File Serving ─────────────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"


@app.get("/")
async def serve_index():
    """Serve the frontend."""
    return FileResponse(static_dir / "index.html")


app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
