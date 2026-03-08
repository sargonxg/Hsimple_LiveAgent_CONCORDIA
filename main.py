# main.py — CONCORDIA FastAPI server

import asyncio
import json
import os
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ontology import OntologyGraph
from agent import MediationAgent
from theories import match_theories

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="CONCORDIA — Live AI Mediation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state (in-memory — one session per deployment)
# ---------------------------------------------------------------------------

graph = OntologyGraph()
agents: Dict[str, MediationAgent] = {}
global_config: Dict = {
    "style": "empathetic",
    "case_type": "workplace",
    "api_key": os.environ.get("GEMINI_API_KEY", ""),
}


def get_or_create_agent(party_id: str) -> MediationAgent:
    if party_id not in agents:
        agents[party_id] = MediationAgent(global_config, graph, party_id)
    return agents[party_id]


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_set": bool(global_config["api_key"] or os.environ.get("GEMINI_API_KEY")),
        "graph_nodes": sum(len(v) for v in graph.entities.values()),
        "agents": list(agents.keys()),
    }


@app.get("/api/case-types")
async def case_types():
    return [
        {"id": "workplace", "name": "Workplace", "icon": "🏢", "description": "Employment & team disputes"},
        {"id": "family", "name": "Family", "icon": "👨‍👩‍👧‍👦", "description": "Family & domestic conflict"},
        {"id": "commercial", "name": "Commercial", "icon": "💼", "description": "Business & contract disputes"},
        {"id": "community", "name": "Community", "icon": "🏘️", "description": "Neighbourhood & civic conflict"},
        {"id": "geopolitical", "name": "Geopolitical", "icon": "🌍", "description": "International & diplomatic disputes"},
    ]


@app.get("/api/styles")
async def styles():
    return [
        {"id": "empathetic", "name": "Empathetic", "icon": "💛", "description": "Warm, relationship focused"},
        {"id": "analytical", "name": "Analytical", "icon": "🔍", "description": "Precise, structured"},
        {"id": "directive", "name": "Directive", "icon": "⚡", "description": "Assertive, efficient"},
    ]


class ConfigRequest(BaseModel):
    style: Optional[str] = None
    case_type: Optional[str] = None
    api_key: Optional[str] = None


@app.post("/api/configure")
async def configure(body: ConfigRequest):
    if body.style:
        global_config["style"] = body.style
    if body.case_type:
        global_config["case_type"] = body.case_type
    if body.api_key:
        global_config["api_key"] = body.api_key
        import google.generativeai as genai
        genai.configure(api_key=body.api_key)
    # Reconfigure all existing agents
    for ag in agents.values():
        ag.reconfigure(global_config)
    return {"status": "ok", "config": {k: ("***" if k == "api_key" and v else v)
                                        for k, v in global_config.items()}}


@app.get("/api/graph")
async def get_graph():
    return graph.to_dict()


@app.get("/api/graph/health")
async def get_health():
    return graph.health_check()


@app.get("/api/theories")
async def get_theories():
    return match_theories(graph.to_dict())


class UploadRequest(BaseModel):
    name: Optional[str] = "Document"
    content: str
    party: Optional[str] = "party_a"


@app.post("/api/upload")
async def upload_document(body: UploadRequest):
    agent = get_or_create_agent(body.party or "party_a")
    summary = await agent.process_document(body.name or "Document", body.content)
    health = graph.health_check()
    return {
        "status": "ok",
        "summary": summary,
        "graph": graph.to_dict(),
        "health": health,
    }


@app.post("/api/reset")
async def reset():
    graph.reset()
    agents.clear()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{party_id}/{session_id}")
async def websocket_endpoint(ws: WebSocket, party_id: str, session_id: str):
    await ws.accept()
    agent = get_or_create_agent(party_id)

    # Send initial state immediately on connect
    await _send_graph_update(ws)

    try:
        while True:
            raw = await ws.receive()

            if "bytes" in raw and raw["bytes"]:
                # Audio PCM — pass to agent if we add audio support later
                # For now, acknowledge
                pass

            elif "text" in raw and raw["text"]:
                try:
                    msg = json.loads(raw["text"])
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "text":
                    await _handle_text(ws, agent, msg.get("content", ""), party_id)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass


async def _handle_text(ws: WebSocket, agent: MediationAgent, text: str, party_id: str):
    """Run agent, stream results back over WebSocket."""
    graph_changed = False
    try:
        async for event in agent.chat(text):
            etype = event.get("type")
            if etype in ("text", "tool_call", "error"):
                await ws.send_json(event)
            elif etype == "graph_update":
                graph_changed = True
    except Exception as exc:
        await ws.send_json({"type": "error", "content": str(exc)})

    # Always send a graph update after processing
    await _send_graph_update(ws)


async def _send_graph_update(ws: WebSocket):
    try:
        await ws.send_json({
            "type": "graph_update",
            "graph": graph.to_dict(),
            "health": graph.health_check(),
        })
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Static files + SPA catch-all
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        # Don't catch API routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404)
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        raise HTTPException(status_code=404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
