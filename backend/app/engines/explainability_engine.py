from typing import Dict, List, Any
from app.models.schemas import (
    DisruptionInput, DisruptionClassification, ImpactAnalysis,
    ExplainabilityReport, RecoveryPlan
)
from app.engines.llm_engine import LLMExplainabilityEngine

class ExplainabilityEngine:
    """
    Synthesizes ML SHAP feature attributions, NetworkX graph dependency cascades,
    rule-based decision trade-offs, and LLM-generated explanations into a coherent report.
    """

    def __init__(self):
        self.llm_engine = LLMExplainabilityEngine()

    def generate_report(
        self,
        disruption: DisruptionInput,
        classification: DisruptionClassification,
        impact: ImpactAnalysis,
        recovery_plans: Dict[str, RecoveryPlan]
    ) -> ExplainabilityReport:

        # 1. ML Prediction Reasoning
        top_shap_items = sorted(
            classification.shap_feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:4]

        ml_reasons = [
            f"Classifier predicted '{classification.predicted_class}' with {classification.confidence * 100:.1f}% confidence.",
        ]
        
        shap_drivers = []
        for feat, val in top_shap_items:
            readable_feat = feat.replace("_", " ").title()
            direction = "increased" if val > 0 else "decreased"
            ml_reasons.append(f"{readable_feat} ({direction} risk score by {abs(val):.3f}).")
            shap_drivers.append({"feature": readable_feat, "shap_value": round(val, 4)})

        # 2. Network Dependency Cascades
        network_cascades = [
            f"Disruption at node '{disruption.location_node_id}' ({disruption.location_name}) impacted {impact.affected_routes_count} active routes.",
            f"Delay cascaded down route dependency sequences affecting {impact.affected_deliveries_count} deliveries.",
            f"{impact.at_risk_sla_count} delivery SLA deadlines are endangered due to projected travel time expansion."
        ]

        # 3. Impact Summary Reasons
        impact_reasons = [
            f"Total cumulative fleet delay across network: {impact.total_expected_delay_minutes:.1f} minutes.",
            f"Vehicles affected: {', '.join([v.vehicle_id for v in impact.affected_vehicles])}."
        ]

        # 4. Plan Comparisons
        plan_a = recovery_plans.get("PLAN_A")
        plan_b = recovery_plans.get("PLAN_B")
        plan_c = recovery_plans.get("PLAN_C")

        plan_comp = {
            "PLAN_A": f"Cost-optimal reroute (${plan_a.total_cost_usd if plan_a else 0} cost, {plan_a.sla_violations_count if plan_a else 0} SLA risk). Best for tight budget.",
            "PLAN_B": f"Speed-optimal fast recovery (${plan_b.total_cost_usd if plan_b else 0} cost, {plan_b.sla_violations_count if plan_b else 0} SLA risk). Best for 100% on-time guarantee.",
            "PLAN_C": f"Reliability/SLA-protected plan (${plan_c.total_cost_usd if plan_c else 0} cost, {plan_c.rescheduled_deliveries_count if plan_c else 0} rescheduled). Best for medical/perishable protection."
        }

        # 5. LLM Natural Language Synthesizer
        disr_dict = disruption.model_dump()
        class_dict = classification.model_dump()
        impact_dict = impact.model_dump()
        plans_dict = {k: v.model_dump() for k, v in recovery_plans.items()}

        llm_summary = self.llm_engine.generate_incident_summary(disr_dict, class_dict)
        llm_plan_comp = self.llm_engine.generate_plan_comparison_explanation(disr_dict, impact_dict, plans_dict)
        llm_notification = self.llm_engine.generate_team_notification(disr_dict, impact_dict)
        llm_provider_info = (
            "External API (Configured)"
            if self.llm_engine.api_key
            else "Deterministic LLM Rule Engine (LLM_API_KEY not set)"
        )

        return ExplainabilityReport(
            ml_prediction_reasoning=ml_reasons,
            shap_top_drivers=shap_drivers,
            network_dependency_cascades=network_cascades,
            impact_summary_reasons=impact_reasons,
            plan_comparisons=plan_comp,
            llm_executive_summary=llm_summary,
            llm_plan_comparison=llm_plan_comp,
            llm_team_notification=llm_notification,
            llm_provider_info=llm_provider_info
        )

