"""
CONCORDIA Resolution Library

Conflict resolution theory database. The AI matches applicable theories
to the current case based on graph characteristics (claim types, escalation
level, interest patterns, leverage balance).

Grounded in TACITUS's 30+ theoretical frameworks.
"""

from __future__ import annotations
from typing import Any

THEORIES = {
    "fisher_ury": {
        "name": "Fisher & Ury — Interest-Based Negotiation",
        "short": "Getting to Yes",
        "school": "Harvard Negotiation Project",
        "principles": [
            "Separate the people from the problem",
            "Focus on interests, not positions",
            "Invent options for mutual gain",
            "Insist on objective criteria",
        ],
        "best_for": ["demand-heavy conflicts", "positional bargaining", "commercial disputes"],
        "techniques": [
            "Ask 'Why?' behind every demand to uncover interests",
            "Brainstorm options before deciding",
            "Use external standards (market rates, legal precedents)",
            "Develop your BATNA (Best Alternative to Negotiated Agreement)",
        ],
        "indicators": {
            "claim_types": ["demand", "proposal"],
            "interest_types": ["economic", "procedural"],
            "min_actors": 2,
        },
    },
    "galtung_triangle": {
        "name": "Galtung — Conflict Triangle",
        "short": "Attitudes, Behavior, Contradictions",
        "school": "Peace Research (Transcend)",
        "principles": [
            "Every conflict has three dimensions: attitudes, behavior, contradictions",
            "Address the root contradiction, not just visible behavior",
            "Distinguish direct violence, structural violence, and cultural violence",
            "Seek transcendence — solutions that transform the conflict itself",
        ],
        "best_for": ["deep-rooted conflicts", "identity disputes", "community conflicts"],
        "techniques": [
            "Map the ABC triangle for each party",
            "Identify structural violence (systemic inequity)",
            "Look for transcendent solutions that redefine the problem",
            "Address cultural narratives that perpetuate conflict",
        ],
        "indicators": {
            "claim_types": ["accusation", "grievance"],
            "interest_types": ["identity", "recognition"],
            "escalation_min": "escalating",
        },
    },
    "glasl_escalation": {
        "name": "Glasl — 9-Stage Escalation Model",
        "short": "De-escalation Mapping",
        "school": "European conflict studies",
        "principles": [
            "Conflicts escalate through predictable stages",
            "Early stages: rational discussion possible",
            "Middle stages: emotional, identity-driven",
            "Late stages: destructive, zero-sum",
            "Intervention must match the escalation stage",
        ],
        "best_for": ["escalating conflicts", "workplace disputes", "relationship breakdown"],
        "techniques": [
            "Identify the current escalation stage",
            "At stages 1-3: facilitate direct dialogue",
            "At stages 4-6: introduce structured mediation",
            "At stages 7-9: require arbitration or power intervention",
            "Always work to de-escalate before resolving",
        ],
        "indicators": {
            "escalation_min": "emerging",
            "has_broken_commitments": True,
        },
    },
    "transformative": {
        "name": "Bush & Folger — Transformative Mediation",
        "short": "Empowerment and Recognition",
        "school": "Relational / transformative",
        "principles": [
            "The goal is transformation of the relationship, not just settlement",
            "Empowerment: help parties regain sense of agency",
            "Recognition: help parties see the other's perspective",
            "The mediator follows the parties, not a fixed process",
        ],
        "best_for": ["relationship conflicts", "family disputes", "ongoing relationships"],
        "techniques": [
            "Reflect and summarize to create recognition moments",
            "Support party decision-making (empowerment)",
            "Don't push toward settlement — trust the process",
            "Highlight moments of understanding between parties",
        ],
        "indicators": {
            "claim_types": ["grievance", "accusation"],
            "interest_types": ["recognition", "identity", "autonomy"],
        },
    },
    "narrative_mediation": {
        "name": "Winslade & Monk — Narrative Mediation",
        "short": "Reauthoring the Story",
        "school": "Social constructionist",
        "principles": [
            "Conflicts are sustained by dominant narratives",
            "People are not the problem — the story is the problem",
            "Alternative stories exist but are marginalized",
            "Reauthoring creates space for new possibilities",
        ],
        "best_for": ["narrative-heavy conflicts", "identity disputes", "cultural conflicts"],
        "techniques": [
            "Map dominant narratives for each party",
            "Externalize the problem ('The conflict' vs 'You are the problem')",
            "Search for 'unique outcomes' — times the conflict story didn't apply",
            "Co-construct a new shared narrative",
        ],
        "indicators": {
            "min_narratives": 2,
            "narrative_frames": ["victim", "villain", "betrayal"],
        },
    },
    "interest_based": {
        "name": "Interest-Based Relational Approach",
        "short": "Preserve relationships while solving problems",
        "school": "ADR / workplace mediation",
        "principles": [
            "Good relationships are the foundation for good outcomes",
            "Separate relationship issues from substantive issues",
            "Be hard on the problem, soft on the person",
        ],
        "best_for": ["workplace conflicts", "team disputes", "ongoing partnerships"],
        "techniques": [
            "Acknowledge emotions before addressing substance",
            "Identify shared goals and values",
            "Create joint problem-solving sessions",
        ],
        "indicators": {
            "interest_types": ["security", "recognition", "procedural"],
            "claim_types": ["grievance", "demand"],
        },
    },
}


def get_applicable_theories(graph) -> list[dict]:
    """Score and rank theories by applicability to the current graph."""
    from .ontology import EscalationLevel

    results = []
    escalation_order = list(EscalationLevel)

    for key, theory in THEORIES.items():
        score = 0
        reasons = []
        indicators = theory.get("indicators", {})

        # Check claim type match
        if "claim_types" in indicators:
            matching = sum(
                1 for c in graph.claims
                if c.claim_type in indicators["claim_types"]
            )
            if matching > 0:
                score += matching * 2
                reasons.append(f"{matching} matching claim types")

        # Check interest type match
        if "interest_types" in indicators:
            matching = sum(
                1 for i in graph.interests
                if i.interest_type in indicators["interest_types"]
            )
            if matching > 0:
                score += matching * 2
                reasons.append(f"{matching} matching interest types")

        # Check escalation level
        if "escalation_min" in indicators:
            min_level = EscalationLevel(indicators["escalation_min"])
            current_idx = escalation_order.index(graph.escalation_level)
            min_idx = escalation_order.index(min_level)
            if current_idx >= min_idx:
                score += 3
                reasons.append(f"escalation at {graph.escalation_level}")

        # Check narrative frames
        if "narrative_frames" in indicators:
            frame_set = set(indicators["narrative_frames"])
            for n in graph.narratives:
                hits = frame_set & set(f.lower() for f in n.frames)
                if hits:
                    score += len(hits) * 2
                    reasons.append(f"narrative frames: {', '.join(hits)}")

        # Check broken commitments
        if indicators.get("has_broken_commitments"):
            broken = sum(1 for c in graph.commitments if c.status == "broken")
            if broken > 0:
                score += broken * 2
                reasons.append(f"{broken} broken commitments")

        # Check minimum actors
        if "min_actors" in indicators:
            if len(graph.actors) >= indicators["min_actors"]:
                score += 1

        # Check minimum narratives
        if "min_narratives" in indicators:
            if len(graph.narratives) >= indicators["min_narratives"]:
                score += 2
                reasons.append(f"{len(graph.narratives)} narratives mapped")

        if score > 0:
            results.append({
                "key": key,
                "name": theory["name"],
                "short": theory["short"],
                "school": theory["school"],
                "score": score,
                "reasons": reasons,
                "principles": theory["principles"][:3],
                "techniques": theory["techniques"][:3],
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_theory_details(theory_name: str, graph) -> dict:
    """Get full theory details with case-specific guidance."""
    theory = THEORIES.get(theory_name)
    if not theory:
        return {"error": f"Unknown theory: {theory_name}. Available: {list(THEORIES.keys())}"}

    # Build case-specific questions based on graph state
    questions = []
    if theory_name == "fisher_ury":
        for actor in graph.actors:
            demands = [c for c in graph.claims if c.source_actor_id == actor.id and c.claim_type == "demand"]
            for d in demands[:2]:
                questions.append(f"What underlying interest drives {actor.name}'s demand: '{d.content[:50]}...'?")

    elif theory_name == "galtung_triangle":
        for actor in graph.actors:
            questions.append(f"What are {actor.name}'s attitudes toward the other party?")
            questions.append(f"What behaviors has {actor.name} exhibited in this conflict?")

    elif theory_name == "transformative":
        for actor in graph.actors:
            questions.append(f"What would help {actor.name} feel empowered in this situation?")
            questions.append(f"What would {actor.name} need to see/hear to recognize the other side?")

    elif theory_name == "narrative_mediation":
        for n in graph.narratives[:3]:
            actor = next((a for a in graph.actors if a.id == n.held_by_actor_id), None)
            if actor:
                questions.append(f"Can you think of a time when {actor.name}'s narrative of '{n.frames[0] if n.frames else 'this situation'}' didn't apply?")

    return {
        **theory,
        "case_specific_questions": questions[:5],
        "actors_in_graph": [a.name for a in graph.actors],
        "current_escalation": str(graph.escalation_level),
    }
