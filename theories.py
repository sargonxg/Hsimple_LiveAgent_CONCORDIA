# theories.py — Conflict resolution theory matching

THEORIES = [
    {
        "id": "interest_based",
        "name": "Interest-Based Negotiation",
        "school": "Harvard Negotiation Project",
        "description": "Focus on underlying interests rather than stated positions to find mutual gains.",
        "principles": [
            "Separate people from the problem",
            "Focus on interests, not positions",
            "Invent options for mutual gain",
            "Use objective criteria",
        ],
        "triggers": {"interests": 2, "claims": 1},
    },
    {
        "id": "transformative",
        "name": "Transformative Mediation",
        "school": "Baruch & Folger",
        "description": "Empower parties and foster mutual recognition to shift the conflict dynamic.",
        "principles": [
            "Empowerment of each party",
            "Recognition of the other party",
            "Support party-driven process",
            "Avoid mediator directiveness",
        ],
        "triggers": {"narratives": 1, "actors": 2},
    },
    {
        "id": "narrative",
        "name": "Narrative Mediation",
        "school": "Winslade & Monk",
        "description": "Explore and re-author the conflict stories to open space for new possibilities.",
        "principles": [
            "Externalize the problem from the person",
            "Explore unique outcomes",
            "Re-author dominant narratives",
            "Build an alternative story",
        ],
        "triggers": {"narratives": 2},
    },
    {
        "id": "evaluative",
        "name": "Evaluative Mediation",
        "school": "Traditional Court-Connected",
        "description": "Mediator provides assessments, reality-testing, and legal risk analysis.",
        "principles": [
            "Reality testing of positions",
            "Legal and factual case assessment",
            "Risk-benefit analysis",
            "Directive guidance toward settlement",
        ],
        "triggers": {"constraints": 2, "claims": 3},
    },
    {
        "id": "problem_solving",
        "name": "Problem-Solving Mediation",
        "school": "Community Mediation",
        "description": "Collaborative problem solving to meet the mutual needs of all parties.",
        "principles": [
            "Define the problem collaboratively",
            "Generate multiple options",
            "Evaluate alternatives objectively",
            "Reach a durable agreement",
        ],
        "triggers": {"interests": 3, "claims": 2},
    },
    {
        "id": "circle_process",
        "name": "Circle Process",
        "school": "Indigenous Peacemaking / Restorative Justice",
        "description": "Community healing and accountability through restorative dialogue circles.",
        "principles": [
            "Shared community values",
            "Storytelling and deep listening",
            "Collective accountability",
            "Holistic healing",
        ],
        "triggers": {"narratives": 2, "actors": 3},
    },
    {
        "id": "principled",
        "name": "Principled Negotiation",
        "school": "Fisher, Ury & Patton — Getting to Yes",
        "description": "Separate people from the problem; focus on interests; generate creative options.",
        "principles": [
            "People: soft on people, hard on problem",
            "Interests: explore motivations behind demands",
            "Options: brainstorm before deciding",
            "Criteria: insist on objective standards",
        ],
        "triggers": {"claims": 2, "interests": 2},
    },
]


def match_theories(graph_data: dict) -> list:
    entities = graph_data.get("entities", {})
    # Normalize: handle both "actors" and "actor" keys
    counts = {}
    for k, v in entities.items():
        key = k.rstrip("s")  # actors -> actor, claims -> claim
        counts[key] = len(v) if isinstance(v, list) else 0
        counts[k] = counts[key]  # also keep plural

    results = []
    for theory in THEORIES:
        score = 0
        matches = []
        for entity_type, required in theory["triggers"].items():
            actual = counts.get(entity_type, 0) or counts.get(entity_type.rstrip("s"), 0)
            if actual >= required:
                score += actual
                matches.append(f"{actual} {entity_type}")

        if score > 0:
            results.append({
                "id": theory["id"],
                "name": theory["name"],
                "school": theory["school"],
                "description": theory["description"],
                "principles": theory["principles"],
                "score": score,
                "reason": f"Matched: {', '.join(matches)}",
                "match_reason": (
                    f"The AI applied {theory['name']} because "
                    f"{' and '.join(matches)} were detected in this case."
                ),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
