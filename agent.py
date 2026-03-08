# agent.py — Gemini-powered mediation agent

import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Any, List

import google.generativeai as genai
import google.generativeai.protos as protos

from ontology import OntologyGraph
from theories import match_theories

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TMPL = """You are CONCORDIA, an expert AI mediator trained in UN conflict resolution methodologies. Your role is to facilitate dialogue, extract structured conflict data, and guide parties toward resolution.

MEDIATOR STYLE: {style}
- empathetic: Warm, validating, relationship-focused. Acknowledge emotions first, then explore needs.
- analytical: Precise, structured. Map issues clearly, identify patterns, use objective frameworks.
- directive: Clear, action-oriented. Challenge positions firmly, guide conversations purposefully.

CASE TYPE: {case_type}
CURRENT PARTY: {party}

YOUR DUAL ROLE:
1. CONVERSATIONAL MEDIATOR — Ask open questions, reflect feelings, reframe, build rapport.
2. ONTOLOGY EXTRACTOR — After each party turn, silently call the appropriate tools to capture what you heard.

EXTRACTION RULES (call tools proactively):
- add_actor → any person, org, or group mentioned
- add_claim → any stated position, demand, or "I want/need X"
- add_interest → any underlying need, motivation, value, or concern (the "why")
- add_constraint → any hard limit, legal requirement, or non-negotiable
- add_leverage → any resource, power, or advantage mentioned
- add_commitment → any promise, agreement, or proposal
- add_event → any specific incident, date, or turning point
- add_narrative → any framing, story, or interpretation of events

Always call at least 1-2 extraction tools per party message, even if you're unsure.

CONVERSATION FLOW:
1. Welcome and open-ended exploration (arrive phase)
2. Structured issue mapping with summaries (structure phase)
3. Interest exploration and reality-testing (verify phase)
4. Resolution generation (resolve phase)

When asked to generate resolution, call: run_health_check(), suggest_applicable_theories(), analyze_common_ground(), generate_resolution_report() — then propose 2-3 concrete resolution paths.
"""

# ---------------------------------------------------------------------------
# Tool declarations
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    protos.FunctionDeclaration(
        name="add_actor",
        description="Add a person, organization, or group involved in the conflict",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "name": protos.Schema(type=protos.Type.STRING, description="Full name"),
                "role": protos.Schema(type=protos.Type.STRING, description="Role: individual, organization, group, institution"),
                "description": protos.Schema(type=protos.Type.STRING, description="Brief description of this actor"),
            },
            required=["name"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_claim",
        description="Add a stated position, demand, or explicit want",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The claim or demand"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Who is making this claim"),
                "strength": protos.Schema(type=protos.Type.STRING, description="Strength: strong, moderate, weak"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_interest",
        description="Add an underlying need, motivation, value, or concern (the 'why' behind a claim)",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The interest or underlying need"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Who holds this interest"),
                "category": protos.Schema(type=protos.Type.STRING, description="Category: economic, social, emotional, procedural, substantive, identity"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_constraint",
        description="Add a hard limitation, boundary, or non-negotiable",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The constraint or limitation"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Who has this constraint"),
                "constraint_type": protos.Schema(type=protos.Type.STRING, description="Type: legal, financial, practical, personal, cultural"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_leverage",
        description="Add a resource, power, or advantage held by a party",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The leverage or advantage"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Who holds this leverage"),
                "leverage_type": protos.Schema(type=protos.Type.STRING, description="Type: legal, financial, social, informational, positional"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_commitment",
        description="Add a promise, agreement, or proposal made by a party",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The commitment or promise"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Who made this commitment"),
                "status": protos.Schema(type=protos.Type.STRING, description="Status: proposed, agreed, broken, conditional"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_event",
        description="Add a specific incident, occurrence, or turning point",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="What happened"),
                "date_approx": protos.Schema(type=protos.Type.STRING, description="Approximate date or timeframe"),
                "impact": protos.Schema(type=protos.Type.STRING, description="Impact level: high, medium, low"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="add_narrative",
        description="Add a party's story, framing, or interpretation of events",
        parameters=protos.Schema(
            type=protos.Type.OBJECT,
            properties={
                "description": protos.Schema(type=protos.Type.STRING, description="The narrative or framing"),
                "actor": protos.Schema(type=protos.Type.STRING, description="Whose narrative this is"),
                "theme": protos.Schema(type=protos.Type.STRING, description="Theme: grievance, identity, fairness, betrayal, vindication"),
            },
            required=["description"],
        ),
    ),
    protos.FunctionDeclaration(
        name="run_health_check",
        description="Check the readiness of the mediation for resolution. Call this to assess progress.",
        parameters=protos.Schema(type=protos.Type.OBJECT, properties={}),
    ),
    protos.FunctionDeclaration(
        name="suggest_applicable_theories",
        description="Identify relevant conflict resolution theories and frameworks for this case.",
        parameters=protos.Schema(type=protos.Type.OBJECT, properties={}),
    ),
    protos.FunctionDeclaration(
        name="analyze_common_ground",
        description="Find shared interests and potential areas of agreement between the parties.",
        parameters=protos.Schema(type=protos.Type.OBJECT, properties={}),
    ),
    protos.FunctionDeclaration(
        name="generate_resolution_report",
        description="Generate a comprehensive resolution analysis with the full ontology data.",
        parameters=protos.Schema(type=protos.Type.OBJECT, properties={}),
    ),
]


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class MediationAgent:
    def __init__(self, config: dict, graph: OntologyGraph, party_id: str):
        self.graph = graph
        self.party_id = party_id
        self.history: List[protos.Content] = []
        self._configure(config)

    def _configure(self, config: dict):
        self.config = config
        api_key = config.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)

        system = SYSTEM_PROMPT_TMPL.format(
            style=config.get("style", "empathetic"),
            case_type=config.get("case_type", "workplace"),
            party="Party A (first party)" if self.party_id == "party_a" else "Party B (second party)",
        )

        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools=[protos.Tool(function_declarations=TOOL_DECLARATIONS)],
            system_instruction=system,
            generation_config=genai.GenerationConfig(temperature=0.7),
        )

    def reconfigure(self, config: dict):
        old_history = self.history[:]
        self._configure(config)
        self.history = old_history

    def _get_chat(self):
        return self.model.start_chat(history=self.history)

    def _execute_tool(self, name: str, args: dict) -> Any:
        """Execute a tool call and return the result."""
        entity_map = {
            "add_actor": "actors",
            "add_claim": "claims",
            "add_interest": "interests",
            "add_constraint": "constraints",
            "add_leverage": "leverages",
            "add_commitment": "commitments",
            "add_event": "events",
            "add_narrative": "narratives",
        }
        if name in entity_map:
            entity_data = {**args, "contributed_by": self.party_id}
            result = self.graph.add_entity(entity_map[name], entity_data)
            return {"status": "added", "id": result.get("id", "unknown")}

        if name == "run_health_check":
            return self.graph.health_check()
        if name == "suggest_applicable_theories":
            return {"theories": match_theories(self.graph.to_dict())}
        if name == "analyze_common_ground":
            return self.graph.common_ground()
        if name == "generate_resolution_report":
            return {
                "health": self.graph.health_check(),
                "common_ground": self.graph.common_ground(),
                "entities": {k: len(v) for k, v in self.graph.entities.items()},
                "relationships": len(self.graph.relationships),
                "theories": match_theories(self.graph.to_dict()),
            }
        return {"error": f"Unknown tool: {name}"}

    async def chat(self, user_text: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message, yielding response events."""
        api_key = self.config.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            yield {"type": "text", "content": (
                "⚠ No Gemini API key configured. Please enter your API key in the "
                "bottom-right corner of the landing page, or set the GEMINI_API_KEY "
                "environment variable."
            ), "author": "system"}
            return

        chat = self._get_chat()

        try:
            # --- Turn 1: send user message ---
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: chat.send_message(user_text)
            )

            # Collect function calls and text from this response
            text_parts = []
            fn_calls = []

            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                if hasattr(part, "function_call") and part.function_call.name:
                    fn_calls.append(part.function_call)

            # Stream text
            if text_parts:
                combined = "".join(text_parts)
                yield {"type": "text", "content": combined, "author": "mediator"}

            # Process tool calls
            tool_response_parts = []
            graph_updated = False

            for fc in fn_calls:
                name = fc.name
                args = dict(fc.args) if fc.args else {}

                yield {"type": "tool_call", "tool": name, "args": args}

                result = self._execute_tool(name, args)
                graph_updated = True

                tool_response_parts.append(
                    protos.Part(
                        function_response=protos.FunctionResponse(
                            name=name,
                            response={"result": json.dumps(result, default=str)},
                        )
                    )
                )

            # --- Turn 2: send tool results, get final response ---
            if tool_response_parts:
                follow_up = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: chat.send_message(
                        protos.Content(role="user", parts=tool_response_parts)
                    ),
                )
                follow_text = []
                for part in follow_up.parts:
                    if hasattr(part, "text") and part.text:
                        follow_text.append(part.text)
                if follow_text:
                    yield {"type": "text", "content": "".join(follow_text), "author": "mediator"}

            # Update history for continuity
            self.history = chat.history

            # Always emit graph update after processing
            if graph_updated or fn_calls:
                yield {"type": "graph_update"}

        except Exception as exc:
            yield {"type": "error", "content": f"Agent error: {exc}"}

    async def process_document(self, name: str, content: str) -> str:
        """Ingest a document and return a summary string."""
        prompt = (
            f"[DOCUMENT INGESTION: {name}]\n\n{content[:4000]}\n\n"
            "Please analyze this document and extract all relevant conflict ontology "
            "elements using the tools. Then provide a 1-2 sentence summary of the "
            "key information this document contains for the mediation."
        )
        summary = ""
        async for event in self.chat(prompt):
            if event["type"] == "text":
                summary += event["content"]
        return (summary[:300] + "...") if len(summary) > 300 else summary or "Document processed."
