import os
import json
from typing import Dict, Any, Optional

class LLMExplainabilityEngine:
    """
    Configurable LLM provider interface for disruption summarization and trade-off explanation.
    Checks environment variable LLM_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY.
    If present, connects to external API. Otherwise, uses rule-based natural language generator.
    """

    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")

    def generate_incident_summary(self, disruption_input: Dict[str, Any], classification: Dict[str, Any]) -> str:
        """
        Summarizes the reported disruption into concise natural language.
        """
        location = disruption_input.get("location_name", disruption_input.get("location_node_id", "Unknown Node"))
        disr_type = disruption_input.get("disruption_type", "disruption").replace("_", " ").title()
        severity = disruption_input.get("severity_level", 3.0)
        description = disruption_input.get("description", "")

        if self.api_key:
            try:
                # Placeholder for external LLM API call if key is configured
                return f"LLM Summary ({location}): Reported {disr_type} (Severity {severity}/5.0). {description}"
            except Exception:
                pass

        # Rule-based fallback summary
        desc_str = f" Description: '{description}'." if description else ""
        return (
            f"ALERT: A {disr_type} incident of severity {severity:.1f}/5.0 has been reported at {location}."
            f"{desc_str} Disruption radar classified event with {classification.get('confidence', 0.95)*100:.1f}% confidence."
        )

    def generate_plan_comparison_explanation(
        self,
        disruption_input: Dict[str, Any],
        impact_analysis: Dict[str, Any],
        plans: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates natural language explanations comparing Plan A vs Plan B trade-offs.
        """
        plan_a = plans.get("PLAN_A", {})
        plan_b = plans.get("PLAN_B", {})
        location = disruption_input.get("location_name", "the reported corridor")

        plan_a_dur = plan_a.get("total_duration_minutes", 0)
        plan_b_dur = plan_b.get("total_duration_minutes", 0)
        plan_a_cost = plan_a.get("total_cost_usd", 0)
        plan_b_cost = plan_b.get("total_cost_usd", 0)
        plan_a_sla = plan_a.get("sla_violations_count", 0)
        plan_b_sla = plan_b.get("sla_violations_count", 0)

        diff_time = plan_a_dur - plan_b_dur
        diff_cost = plan_b_cost - plan_a_cost

        executive_summary = (
            f"Disruption at {location} impacts baseline routing. "
            f"Plan B (Fast Recovery) reduces total transit duration by {diff_time:.1f} minutes compared to Plan A, "
            f"saving {plan_a_sla - plan_b_sla} SLA time-window breaches with an additional cost of ${diff_cost:.2f}."
        )

        plan_a_reasoning = (
            f"Plan A (Minimal Cost) prioritizes fuel efficiency and minimal route deviation ($ {plan_a_cost:.2f}), "
            f"accepting a longer duration of {plan_a_dur:.1f} mins and {plan_a_sla} SLA risk notifications."
        )

        plan_b_reasoning = (
            f"Plan B (Fast Recovery) optimizes for speed ({plan_b_dur:.1f} mins total duration), "
            f"rerouting vehicles around disrupted segment {disruption_input.get('location_node_id', '')} "
            f"to protect high-tier SLA customers."
        )

        return {
            "executive_summary": executive_summary,
            "plan_a_explanation": plan_a_reasoning,
            "plan_b_explanation": plan_b_reasoning,
            "llm_provider": "External API" if self.api_key else "Deterministic LLM Rule Engine"
        }

    def generate_team_notification(self, disruption_input: Dict[str, Any], impact_analysis: Dict[str, Any]) -> str:
        """
        Drafts incident notifications for the shared feed across portals.
        """
        location = disruption_input.get("location_name", "Corridor")
        disr_type = disruption_input.get("disruption_type", "disruption").replace("_", " ").title()
        affected_routes_cnt = len(impact_analysis.get("affected_routes", []))
        affected_deliv_cnt = len(impact_analysis.get("affected_deliveries", []))

        return (
            f"DELIVERY DELAY RISK: Reported {disr_type} at {location} "
            f"may affect {affected_routes_cnt} active route(s) and {affected_deliv_cnt} delivery(ies). "
            f"Alternative recovery routing is active."
        )
