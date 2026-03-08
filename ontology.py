# ontology.py — In-memory knowledge graph for conflict ontology

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


ENTITY_TYPES = ["actors", "claims", "interests", "constraints",
                "leverages", "commitments", "events", "narratives"]


class OntologyGraph:
    def __init__(self):
        self.reset()

    def reset(self):
        self.entities: Dict[str, List[Dict]] = {t: [] for t in ENTITY_TYPES}
        self.relationships: List[Dict] = []
        self.title: str = ""
        self.summary: str = ""
        self.phase: str = "arrive"
        self.escalation_level: str = "moderate"

    def add_entity(self, entity_type: str, data: Dict) -> Dict:
        """Add or update an entity. Returns the entity dict."""
        if entity_type not in self.entities:
            # Try singular -> plural
            plural = entity_type + "s"
            if plural in self.entities:
                entity_type = plural
            else:
                return {"error": f"Unknown entity type: {entity_type}"}

        # Deduplicate by name/description (case-insensitive)
        key_field = "name" if "name" in data else "description"
        key = (data.get(key_field) or "").strip().lower()
        if key:
            for existing in self.entities[entity_type]:
                ex_key = (existing.get(key_field) or "").strip().lower()
                if ex_key == key:
                    existing.update({k: v for k, v in data.items() if v})
                    self._update_derived()
                    return existing

        entity = {
            "id": f"{entity_type.rstrip('s')}_{uuid.uuid4().hex[:8]}",
            "created_at": datetime.utcnow().isoformat(),
            **data,
        }
        self.entities[entity_type].append(entity)
        self._update_derived()
        return entity

    def _update_derived(self):
        """Recompute relationships, phase, title, summary."""
        self._rebuild_relationships()
        self._update_phase()
        self._update_title()

    def _rebuild_relationships(self):
        self.relationships = []
        actors = self.entities["actors"]
        actor_map = {a.get("name", "").lower(): a["id"] for a in actors if "name" in a}

        def link(actor_name: str, entity_id: str, rel_type: str):
            aid = actor_map.get((actor_name or "").lower())
            if aid and aid != entity_id:
                self.relationships.append({
                    "source": aid, "target": entity_id,
                    "type": rel_type, "auto": True,
                })

        for e in self.entities["claims"]:
            link(e.get("actor"), e["id"], "makes_claim")
        for e in self.entities["interests"]:
            link(e.get("actor"), e["id"], "has_interest")
        for e in self.entities["constraints"]:
            link(e.get("actor"), e["id"], "subject_to")
        for e in self.entities["leverages"]:
            link(e.get("actor"), e["id"], "holds_leverage")
        for e in self.entities["commitments"]:
            link(e.get("actor"), e["id"], "made_commitment")
        for e in self.entities["narratives"]:
            link(e.get("actor"), e["id"], "holds_narrative")

    def _update_phase(self):
        total = sum(len(v) for v in self.entities.values())
        hc = self.quick_score()
        if hc >= 75:
            self.phase = "resolve"
        elif hc >= 40 or total > 10:
            self.phase = "verify"
        elif total > 4:
            self.phase = "structure"
        else:
            self.phase = "arrive"

    def _update_title(self):
        actors = self.entities["actors"]
        if not self.title and len(actors) >= 2:
            a = actors[0].get("name", "Party A")
            b = actors[1].get("name", "Party B")
            self.title = f"{a} & {b} — Mediation"
        elif not self.title and len(actors) == 1:
            self.title = f"{actors[0].get('name', 'Party A')} — Mediation"

    def quick_score(self) -> int:
        e = self.entities
        checks = [
            len(e["actors"]) >= 2,
            len(e["claims"]) >= 1,
            len(e["interests"]) >= 1,
            len(e["constraints"]) >= 1,
            self._both_parties_heard(),
            len(e["events"]) >= 1,
            len(e["interests"]) >= len(e["claims"]),
            sum(len(v) for v in e.values()) >= 8,
        ]
        return int(sum(checks) / len(checks) * 100)

    def health_check(self) -> Dict:
        e = self.entities
        checks = [
            {"name": "actors_identified", "description": "Both parties identified",
             "passed": len(e["actors"]) >= 2},
            {"name": "claims_extracted", "description": "Claims documented",
             "passed": len(e["claims"]) >= 1},
            {"name": "interests_explored", "description": "Underlying interests explored",
             "passed": len(e["interests"]) >= 1},
            {"name": "constraints_known", "description": "Constraints identified",
             "passed": len(e["constraints"]) >= 1},
            {"name": "both_parties_heard", "description": "Both parties have shared perspectives",
             "passed": self._both_parties_heard()},
            {"name": "events_documented", "description": "Key events documented",
             "passed": len(e["events"]) >= 1},
            {"name": "interests_depth", "description": "More interests than claims (depth)",
             "passed": len(e["interests"]) >= len(e["claims"])},
            {"name": "sufficient_data", "description": "Sufficient data for resolution",
             "passed": sum(len(v) for v in e.values()) >= 8},
        ]

        passed = sum(1 for c in checks if c["passed"])
        score = int(passed / len(checks) * 100)

        gap_msgs = {
            "actors_identified": "Need to identify all parties involved",
            "claims_extracted": "Need to document the stated positions",
            "interests_explored": "Need to explore underlying needs and motivations",
            "constraints_known": "Need to understand limitations and non-negotiables",
            "both_parties_heard": "Party 2 has not yet shared their perspective",
            "events_documented": "Need to document key incidents and turning points",
            "interests_depth": "Explore deeper motivations behind stated positions",
            "sufficient_data": "Need more information from both parties",
        }
        gaps = [gap_msgs[c["name"]] for c in checks if not c["passed"]]

        per_party = {
            "party_a": {"score": self._party_score("party_a")},
            "party_b": {"score": self._party_score("party_b")},
        }

        self._update_phase()
        return {
            "score": score,
            "checks": checks,
            "gaps": gaps,
            "phase": self.phase,
            "per_party": per_party,
        }

    def _both_parties_heard(self) -> bool:
        parties = set()
        for items in self.entities.values():
            for e in items:
                if e.get("contributed_by"):
                    parties.add(e["contributed_by"])
        return len(parties) >= 2

    def _party_score(self, party_id: str) -> int:
        count = sum(
            1 for items in self.entities.values()
            for e in items if e.get("contributed_by") == party_id
        )
        return min(100, count * 10)

    def common_ground(self) -> Dict:
        interests = self.entities["interests"]
        shared = []
        a_interests = [i for i in interests if i.get("contributed_by") == "party_a"]
        b_interests = [i for i in interests if i.get("contributed_by") == "party_b"]

        stop_words = {"the", "a", "an", "to", "for", "of", "in", "and", "or",
                      "is", "are", "was", "were", "be", "been", "have", "has",
                      "my", "their", "our", "i", "we", "they", "that", "this"}
        for ia in a_interests:
            for ib in b_interests:
                wa = set(ia.get("description", "").lower().split()) - stop_words
                wb = set(ib.get("description", "").lower().split()) - stop_words
                overlap = wa & wb
                if len(overlap) >= 2:
                    shared.append({
                        "party_a": ia.get("description"),
                        "party_b": ib.get("description"),
                        "overlap": list(overlap),
                    })
        return {"shared_interests": shared, "count": len(shared)}

    def to_dict(self) -> Dict:
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "title": self.title,
            "summary": self.summary,
            "phase": self.phase,
            "escalation_level": self.escalation_level,
        }
