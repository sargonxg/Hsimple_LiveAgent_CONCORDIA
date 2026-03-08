"""
CONCORDIA Case Types

Different dispute categories that adjust the ontology focus,
probing questions, and applicable theories.
"""

CASE_TYPES = {
    "workplace": {
        "name": "Workplace / HR Dispute",
        "icon": "🏢",
        "description": "Team conflicts, management issues, harassment, termination disputes",
        "focus_interests": ["recognition", "procedural", "security", "autonomy"],
        "focus_claims": ["grievance", "accusation", "demand"],
        "context_prompt": """This is a WORKPLACE dispute. Focus on:
- Organizational hierarchy and reporting relationships
- HR policies and procedures that apply
- Power dynamics between managers and reports
- Documentation and paper trails
- Professional reputation and career impact
- Company culture and norms
- Legal/regulatory frameworks (employment law)""",
        "probing_questions": [
            "What is the reporting relationship between the parties?",
            "Are there HR policies or procedures that apply here?",
            "Has this been documented formally? Emails, written complaints?",
            "How has this affected the team or work environment?",
            "What outcome would allow both people to continue working effectively?",
        ],
    },
    "family": {
        "name": "Family / Relationship Dispute",
        "icon": "👨\u200d👩\u200d👧\u200d👦",
        "description": "Divorce, custody, inheritance, family business, elder care",
        "focus_interests": ["identity", "recognition", "security", "autonomy"],
        "focus_claims": ["grievance", "demand", "accusation"],
        "context_prompt": """This is a FAMILY dispute. Focus on:
- Emotional bonds and relationship history
- Children's wellbeing (if applicable)
- Family dynamics and alliances
- Shared history and memories
- Financial interdependence
- Cultural and religious values
- Long-term relationship preservation vs. separation""",
        "probing_questions": [
            "How long have you known each other? What's the relationship history?",
            "Are there children or dependents affected by this situation?",
            "What would an ideal family relationship look like after this is resolved?",
            "Are there other family members whose perspectives matter?",
            "What shared values or memories still connect you?",
        ],
    },
    "commercial": {
        "name": "Commercial / Business Dispute",
        "icon": "💼",
        "description": "Contract disputes, partnership conflicts, vendor issues, IP",
        "focus_interests": ["economic", "procedural", "security"],
        "focus_claims": ["demand", "justification", "proposal"],
        "context_prompt": """This is a COMMERCIAL dispute. Focus on:
- Contract terms and obligations
- Financial amounts and timelines
- Business relationships and reputation
- Industry standards and practices
- Legal remedies available
- Ongoing business needs vs. one-time resolution
- Opportunity costs of continued conflict""",
        "probing_questions": [
            "Is there a written contract or agreement?",
            "What are the specific financial amounts in dispute?",
            "What are the alternatives if this doesn't resolve? (litigation costs, etc.)",
            "Is this an ongoing business relationship you want to preserve?",
            "What industry standards or benchmarks apply here?",
        ],
    },
    "community": {
        "name": "Community / Neighborhood Dispute",
        "icon": "🏘️",
        "description": "Neighbor conflicts, HOA issues, local government, shared spaces",
        "focus_interests": ["security", "autonomy", "identity", "recognition"],
        "focus_claims": ["grievance", "demand", "accusation"],
        "context_prompt": """This is a COMMUNITY dispute. Focus on:
- Shared physical space and proximity
- Community norms and expectations
- Quality of life and daily impact
- Local regulations and bylaws
- Long-term coexistence (can't just walk away)
- Cultural diversity and differences
- Community resources and mediating institutions""",
        "probing_questions": [
            "How long have you been neighbors/community members?",
            "How does this conflict affect your daily life?",
            "Are there community rules, HOA bylaws, or local regulations that apply?",
            "Are other community members affected?",
            "What would peaceful coexistence look like?",
        ],
    },
    "geopolitical": {
        "name": "Geopolitical / International Dispute",
        "icon": "🌍",
        "description": "State conflicts, territorial disputes, sanctions, treaty negotiations",
        "focus_interests": ["security", "autonomy", "economic", "identity"],
        "focus_claims": ["demand", "accusation", "justification", "grievance"],
        "context_prompt": """This is a GEOPOLITICAL dispute. Focus on:
- Sovereignty and territorial integrity
- Security interests and threat perceptions
- International law and treaty obligations
- Historical grievances and collective memory
- Alliance structures and external actors
- Economic interdependence and sanctions
- Domestic political constraints on negotiations""",
        "probing_questions": [
            "What are the core sovereignty or territorial issues?",
            "What security concerns drive each side's position?",
            "Are there international legal frameworks that apply?",
            "What historical events shaped the current conflict?",
            "Which external actors or alliances influence the situation?",
        ],
    },
}

def get_case_type(case_type: str) -> dict:
    return CASE_TYPES.get(case_type, CASE_TYPES["workplace"])

def get_all_case_types() -> dict:
    return {k: {"name": v["name"], "icon": v["icon"], "description": v["description"]}
            for k, v in CASE_TYPES.items()}
