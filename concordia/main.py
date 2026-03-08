"""
CONCORDIA — FastAPI Bidi-Streaming Server

Multi-party mediation server with:
  - WebSocket bidi-streaming for real-time mediation (ADK Live API)
  - REST API for graph state, health, configuration, document upload
  - Runtime agent reconfiguration (mediator style + case type)
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


# ── Request/Response Models ──────────────────────────────────────────────────

class ApiKeyRequest(PydanticBaseModel):
    key: str


class UploadDocumentRequest(PydanticBaseModel):
    party_id: str = "party1"
    text: str
    document_name: str = "Uploaded Document"


class ConfigureRequest(PydanticBaseModel):
    mediator_style: str = "empathetic"  # empathetic, analytical, directive
    case_type: str = "workplace"  # workplace, family, commercial, community, geopolitical


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


# ── REST Endpoints — Configuration ──────────────────────────────────────────

@app.post("/api/set-key")
async def set_api_key(req: ApiKeyRequest):
    """Set the Gemini API key at runtime (demo only)."""
    os.environ["GOOGLE_API_KEY"] = req.key
    logger.info("API key updated at runtime.")
    return {"status": "ok"}


@app.post("/api/configure")
async def configure(req: ConfigureRequest):
    """Reconfigure mediator style and case type. Rebuilds agent hierarchy."""
    import concordia_agent
    new_root = build_agents(req.mediator_style, req.case_type)
    concordia_agent.root_agent = new_root
    # Rebuild runner with new agent
    global runner
    runner = Runner(app_name=APP_NAME, agent=new_root, session_service=session_service)
    logger.info(f"Reconfigured: style={req.mediator_style}, case_type={req.case_type}")
    return {
        "status": "configured",
        "mediator_style": req.mediator_style,
        "case_type": req.case_type,
    }


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
    from concordia_agent.ontology import ConflictGraph
    ontology.graph = ConflictGraph()
    ontology.active_party = "default"
    # Update the module-level reference
    import concordia_agent
    concordia_agent.graph = ontology.graph
    logger.info("Graph reset.")
    return {"status": "reset"}


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

    # Send initial graph state
    try:
        await websocket.send_json({
            "type": "graph_update",
            "graph": json.loads(graph.model_dump_json()),
            "health": graph.health_check(),
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
