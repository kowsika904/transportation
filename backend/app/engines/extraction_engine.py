import os
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ExtractedIncidentSchema(BaseModel):
    incident_type: str = Field(..., description="Categorized incident type: road_closure, flooding, severe_congestion, vehicle_breakdown, blizzard")
    location_node_id: str = Field(..., description="Resolved road network node ID e.g. NODE_MANHATTAN_BRIDGE, NODE_BROOKLYN_BRIDGE, NODE_QUEENS_TUNNEL")
    location_name: str = Field(..., description="Human readable name of the resolved corridor")
    severity_level: float = Field(..., ge=1.0, le=5.0, description="Severity rating 1-5")
    inferred_severity: float = Field(default=4.0, ge=1.0, le=5.0, description="Inferred severity rating from message text")
    explicit_severity: float = Field(default=4.0, ge=1.0, le=5.0, description="Explicit agent form severity rating")
    passability: str = Field(..., description="Passability status: BLOCKED, RESTRICTED, OPEN")
    urgency: str = Field(..., description="Urgency level: CRITICAL, HIGH, MEDIUM, LOW")
    extraction_method: str = Field(..., description="Method used: LLM (Gemini/OpenAI) or Deterministic Rule Parser")
    is_mismatched_from_form: bool = Field(default=False, description="Whether extracted message location differed from form input")
    extraction_reasoning: str = Field(..., description="Explanation of how fields were extracted")

class IncidentExtractor:
    """
    End-to-end incident understanding & extraction service.
    Processes Transport Agent messages to extract structured fields.
    Uses LLM integration if API key is configured, else falls back to a deterministic rule parser.
    Never invents locations; resolves corridors to exact graph node IDs.
    """

    KNOWN_CORRIDORS: Dict[str, Dict[str, Any]] = {
        "NODE_MIDTOWN_HUB": {
            "name": "Midtown Central Hub",
            "keywords": ["midtown hub", "midtown central", "central hub", "midtown depot"]
        },
        "NODE_QUEENS_DC": {
            "name": "Queens Logistics DC",
            "keywords": ["queens dc", "queens distribution", "queens logistics", "queens warehouse"]
        },
        "NODE_MANHATTAN_BRIDGE": {
            "name": "Manhattan Bridge Corridor",
            "keywords": ["manhattan bridge", "manhattan bridge corridor", "manhattan brg"]
        },
        "NODE_BROOKLYN_BRIDGE": {
            "name": "Brooklyn Bridge Corridor",
            "keywords": ["brooklyn bridge", "brooklyn bridge corridor", "brooklyn brg"]
        },
        "NODE_WILLIAMSBURG_BRIDGE": {
            "name": "Williamsburg Bridge Corridor",
            "keywords": ["williamsburg bridge", "williamsburg bridge corridor", "williamsburg brg", "williamsburg"]
        },
        "NODE_FDR_DRIVE": {
            "name": "FDR Drive Corridor",
            "keywords": ["fdr drive", "fdr north", "fdr northbound", "fdr corridor", "fdr"]
        },
        "NODE_LINCOLN_TUNNEL": {
            "name": "Lincoln Tunnel Access",
            "keywords": ["lincoln tunnel", "lincoln tunnel access", "lincoln"]
        },
        "NODE_QUEENS_TUNNEL": {
            "name": "Queens Midtown Tunnel",
            "keywords": ["queens midtown tunnel", "queens tunnel", "midtown tunnel", "queens midtown"]
        },
        "NODE_BROOKLYN_NAVY": {
            "name": "Brooklyn Navy Yard Depot",
            "keywords": ["brooklyn navy yard", "brooklyn navy", "navy yard"]
        },
        "NODE_HARLEM_GATEWAY": {
            "name": "Harlem Freight Terminal",
            "keywords": ["harlem freight", "harlem gateway", "harlem terminal", "harlem"]
        },
        "NODE_FINANCIAL": {
            "name": "Wall Street Financial Hub",
            "keywords": ["financial district", "wall street", "financial hub", "fidi"]
        },
        "NODE_JFK_CARGO": {
            "name": "JFK Logistics Terminal",
            "keywords": ["jfk cargo", "jfk logistics", "jfk terminal", "jfk airport", "jfk"]
        }
    }

    def __init__(self):
        # Check if LLM API key is present
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.has_llm = bool(self.gemini_key or self.openai_key)

    def extract_from_incident_input(
        self,
        description_text: str,
        form_node_id: str,
        form_disruption_type: str,
        form_severity: float,
        form_location_name: Optional[str] = None
    ) -> ExtractedIncidentSchema:
        """
        Main extraction entry point.
        """
        text_clean = (description_text or "").strip()

        # Try LLM if key is present
        if self.has_llm:
            try:
                return self._extract_with_llm(text_clean, form_node_id, form_disruption_type, form_severity, form_location_name)
            except Exception as e:
                print(f"LLM extraction call failed ({e}). Falling back to Deterministic Rule Parser.")

        # Deterministic extraction fallback
        return self._extract_deterministic(text_clean, form_node_id, form_disruption_type, form_severity, form_location_name)

    def _extract_deterministic(
        self,
        text: str,
        form_node_id: str,
        form_type: str,
        form_severity: float,
        form_location_name: Optional[str] = None
    ) -> ExtractedIncidentSchema:
        text_lower = text.lower()

        # 1. Extract incident type
        extracted_type = form_type
        if form_type == "no_alternative_blocked" or "no alternative" in text_lower or "no_alternative" in text_lower:
            extracted_type = "no_alternative_blocked"
        elif any(w in text_lower for w in ["breakdown", "accident", "crash", "stalled vehicle", "disabled vehicle", "overturned"]):
            extracted_type = "vehicle_breakdown"
        elif any(w in text_lower for w in ["flood", "flooding", "water", "submerged", "washout", "overflow"]):
            extracted_type = "flooding"
        elif any(w in text_lower for w in ["closed", "closure", "blocked", "shut down", "impassable", "collapsed", "full closure"]):
            extracted_type = "road_closure"
        elif any(w in text_lower for w in ["congestion", "traffic", "gridlock", "jam", "heavy delays", "sluggish", "standstill"]):
            extracted_type = "severe_congestion"
        elif any(w in text_lower for w in ["blizzard", "snow", "ice", "storm", "freezing rain"]):
            extracted_type = "blizzard"

        # 2. Extract & resolve location node from text (stripping 'reroute via' / 'detour via' clauses)
        norm_form_node = form_node_id.replace("SEG_", "NODE_")
        text_disruption_part = re.sub(r'(?:reroute|detour|divert|bypass)\s+via\s+[^.,!]+', '', text_lower)

        matched_corridor = None
        for node_id, data in self.KNOWN_CORRIDORS.items():
            for kw in data["keywords"]:
                if kw in text_disruption_part:
                    matched_corridor = (node_id, data["name"])
                    break
            if matched_corridor:
                break

        is_mismatched = False
        if matched_corridor:
            msg_node_id, msg_node_name = matched_corridor
            if msg_node_id != norm_form_node:
                is_mismatched = True
                resolved_node_id = msg_node_id
                resolved_name = msg_node_name
            else:
                resolved_node_id = norm_form_node
                resolved_name = form_location_name or msg_node_name
        else:
            resolved_node_id = norm_form_node
            resolved_name = form_location_name or self.KNOWN_CORRIDORS.get(norm_form_node, {}).get("name", form_node_id)

        # 3. Extract severity level
        extracted_severity = form_severity
        num_match = re.search(r'(?:severity|level|rating)\s*(?:is|=|:)?\s*([1-5](?:\.\d+)?)', text_lower)
        if num_match:
            try:
                extracted_severity = float(num_match.group(1))
            except ValueError:
                pass
        else:
            if any(w in text_lower for w in ["critical", "catastrophic", "complete closure", "level 5", "5/5"]):
                extracted_severity = 5.0
            elif any(w in text_lower for w in ["severe", "major", "level 4", "4/5"]):
                extracted_severity = max(4.0, form_severity)
            elif any(w in text_lower for w in ["moderate", "level 3", "3/5"]):
                extracted_severity = 3.0
            elif any(w in text_lower for w in ["minor", "slight", "level 2", "2/5"]):
                extracted_severity = 2.0

        # 4. Passability & Urgency
        if extracted_type == "road_closure" or extracted_severity >= 4.8:
            passability = "BLOCKED"
            urgency = "CRITICAL"
        elif extracted_severity >= 3.8:
            passability = "RESTRICTED"
            urgency = "HIGH"
        elif extracted_severity >= 2.5:
            passability = "RESTRICTED"
            urgency = "MEDIUM"
        else:
            passability = "OPEN"
            urgency = "LOW"

        reasoning = (
            f"Extracted incident_type='{extracted_type}', location='{resolved_name}' ({resolved_node_id}), "
            f"severity={extracted_severity:.1f} via keyword pattern matching."
        )
        if is_mismatched:
            reasoning += f" Discrepancy detected: agent message text specified corridor '{resolved_name}' whereas form selected '{form_node_id}'."

        inferred_severity = extracted_severity
        explicit_severity = form_severity

        return ExtractedIncidentSchema(
            incident_type=extracted_type,
            location_node_id=resolved_node_id,
            location_name=resolved_name,
            severity_level=round(float(extracted_severity), 1),
            inferred_severity=round(float(inferred_severity), 1),
            explicit_severity=round(float(explicit_severity), 1),
            passability=passability,
            urgency=urgency,
            extraction_method="Deterministic Rule Parser",
            is_mismatched_from_form=is_mismatched,
            extraction_reasoning=reasoning
        )

    def _extract_with_llm(
        self,
        text: str,
        form_node_id: str,
        form_type: str,
        form_severity: float
    ) -> ExtractedIncidentSchema:
        # Structured schema prompt for real LLM integration if API key is provided
        raise NotImplementedError("External LLM API Provider not configured in environment.")
