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

    "principled_negotiation": {
        "name": "Principled Negotiation — ZOPA Analysis",
        "short": "Zone of Possible Agreement",
        "school": "Negotiation theory",
        "principles": [
            "Map the Zone of Possible Agreement (ZOPA) — the overlap between parties' bottom lines",
            "Every party has a reservation point — the point beyond which they prefer no deal",
            "Expanding the pie: find ways to create value before dividing it",
            "Package trades across multiple issues rather than splitting single issues",
        ],
        "best_for": ["multi-issue negotiations", "commercial disputes", "distributive bargaining"],
        "techniques": [
            "Map each party's BATNA, reservation point, and aspirations",
            "Identify logrolling opportunities — trade lower-priority items for higher-priority ones",
            "Use post-settlement settlement: after agreement, look for improvements",
            "Anchor strategically and counter-anchor with objective justification",
            "Sequence concessions: slow early, faster later signals good faith",
        ],
        "indicators": {
            "claim_types": ["demand", "proposal", "justification"],
            "interest_types": ["economic", "procedural"],
            "min_actors": 2,
        },
    },

    "rights_based": {
        "name": "Rights-Based Framework",
        "short": "Normative standards and entitlements",
        "school": "Legal / human rights",
        "principles": [
            "Parties have legal, contractual, or moral rights that define the dispute",
            "Rights set the floor: no agreement should violate established entitlements",
            "Rights provide objective benchmarks for fairness",
            "Procedural rights (due process) are as important as substantive rights",
        ],
        "best_for": ["employment law disputes", "contractual breaches", "discrimination claims", "rights violations"],
        "techniques": [
            "Identify all applicable rights: legal, contractual, human rights standards",
            "Map which rights are violated and by whom",
            "Use rights as a floor for negotiation — not a ceiling",
            "Frame proposals in terms of rights fulfillment, not concessions",
            "Consider declaratory relief: sometimes formal acknowledgment of a rights violation matters more than compensation",
        ],
        "indicators": {
            "claim_types": ["accusation", "grievance", "justification"],
            "interest_types": ["procedural", "security", "autonomy"],
            "escalation_min": "emerging",
        },
    },

    "power_based": {
        "name": "Power Analysis — Strategic Leverage",
        "short": "Map and rebalance power dynamics",
        "school": "Critical conflict theory",
        "principles": [
            "Power asymmetry is the root of most intractable conflicts",
            "Sustainable agreements require sufficient power balance",
            "Coercive power escalates; normative and relational power builds trust",
            "Empower weaker parties before negotiating — otherwise agreements don't hold",
        ],
        "best_for": ["power-imbalanced disputes", "labor conflicts", "colonial/institutional conflicts"],
        "techniques": [
            "Map all sources of power for each party (coercive, reward, informational, normative, relational, structural)",
            "Identify power-equalizing interventions: legal aid, coalitions, information",
            "Protect weaker parties from coercive pressure during negotiation",
            "Help stronger parties understand that domination produces unstable outcomes",
            "Reframe leverage: shift from coercive to normative or relational power",
        ],
        "indicators": {
            "interest_types": ["autonomy", "security", "economic"],
            "escalation_min": "escalating",
        },
    },

    "restorative_justice": {
        "name": "Restorative Justice Framework",
        "short": "Repair harm, rebuild relationships",
        "school": "Restorative justice (Zehr, Pranis)",
        "principles": [
            "Crime and conflict are violations of relationships, not just rules",
            "Restorative questions: What harm was done? What are the needs? Who is responsible?",
            "Both harmed party and responsible party need to be central to the process",
            "The goal is repair, not punishment",
        ],
        "best_for": ["post-harm situations", "trust violations", "community harm", "workplace incidents"],
        "techniques": [
            "Hold a restorative conference: harmed party, responsible party, supporters",
            "Use restorative questions to map impact and needs",
            "Build a repair plan together — concrete, time-bound actions",
            "Include community members if wider harm occurred",
            "Follow up to verify repairs were made — accountability is ongoing",
        ],
        "indicators": {
            "claim_types": ["accusation", "grievance"],
            "interest_types": ["recognition", "security"],
            "has_broken_commitments": True,
        },
    },

    "circle_process": {
        "name": "Peacemaking Circles (Pranis)",
        "short": "Community healing and shared values",
        "school": "Indigenous / community peacemaking",
        "principles": [
            "The circle creates equal standing for all voices",
            "A talking piece ensures each person speaks without interruption",
            "Shared values are identified before addressing the problem",
            "Consensus is sought — no one is voted down",
        ],
        "best_for": ["community conflicts", "school disputes", "multi-party harm", "collective trauma"],
        "techniques": [
            "Open with a ceremony or check-in to establish tone",
            "Identify shared values: what do all parties care about?",
            "Use a talking piece for structured storytelling",
            "Circle keeper: guide the process without directing the outcome",
            "Close with a consensus agreement — everyone must be able to live with the outcome",
        ],
        "indicators": {
            "interest_types": ["identity", "recognition", "security"],
            "min_narratives": 2,
            "escalation_min": "emerging",
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

    elif theory_name == "principled_negotiation":
        for actor in graph.actors:
            questions.append(f"What is {actor.name}'s best alternative if no agreement is reached (BATNA)?")
            questions.append(f"What is the minimum {actor.name} would accept (reservation point)?")

    elif theory_name == "rights_based":
        questions.append("What legal or contractual rights are relevant to this dispute?")
        questions.append("Have any of these rights been formally violated, and how?")
        questions.append("What procedural rights (fair process) are at stake?")

    elif theory_name == "power_based":
        for actor in graph.actors:
            leverages = [l for l in graph.leverages if l.held_by_actor_id == actor.id]
            if leverages:
                questions.append(f"How does {actor.name} use their leverage constructively rather than coercively?")
        questions.append("What would a power-balanced negotiation process look like here?")

    elif theory_name == "restorative_justice":
        questions.append("Who has been harmed and how?")
        questions.append("What does the harmed party need to feel repaired?")
        questions.append("What can the responsible party do to make things right?")

    elif theory_name == "circle_process":
        questions.append("What shared values can all parties agree on before addressing the problem?")
        questions.append("Who from the community should be part of the circle?")
        questions.append("What would consensus — an outcome everyone can live with — look like?")

    return {
        **theory,
        "case_specific_questions": questions[:5],
        "actors_in_graph": [a.name for a in graph.actors],
        "current_escalation": str(graph.escalation_level),
    }
