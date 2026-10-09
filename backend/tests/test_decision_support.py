import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.loader import DataLoader
from app.engines.recovery_engine import ORToolsRecoveryEngine
from app.engines.decision_support_engine import DecisionSupportEngine
from app.models.schemas import DisruptionInput, PriorityItem
from app.api.auth import TEST_SUITE_TOKEN
from app.db.repository import DatabaseRepository

client = TestClient(app)
headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

def test_decision_support_engine_policies():
    loader = DataLoader()
    engine = DecisionSupportEngine()
    recovery_engine = ORToolsRecoveryEngine(loader)

    disr = DisruptionInput(
        disruption_id="TEST_DECISION_01",
        disruption_type="blizzard",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=4.8
    )

    p_items = [
        PriorityItem(
            delivery_id="DELIV_101",
            customer_name="Apex Medical Supplies Hub",
            priority_score=95.0,
            priority_tier="CRITICAL",
            sla_end_time="10:30",
            minutes_until_sla=15.0,
            delay_minutes=75.0,
            item_value_usd=25000.0,
            is_perishable=True,
            penalty_usd_per_hour_late=500.0,
            score_breakdown={},
            reasoning="Critical medical"
        )
    ]

    plans = recovery_engine.generate_recovery_plans(disr, p_items)

    # 1. Test MINIMIZE_COST Policy
    rec_cost = engine.evaluate_recommendation(plans, policy="MINIMIZE_COST", prioritized_deliveries=p_items)
    assert rec_cost.recommended_plan_id in ["PLAN_A", "PLAN_B", "PLAN_C"]
    assert rec_cost.policy_used == "MINIMIZE_COST"
    assert "cost_weight" in rec_cost.criteria_and_weights

    # 2. Test MINIMIZE_DELAY Policy
    rec_delay = engine.evaluate_recommendation(plans, policy="MINIMIZE_DELAY", prioritized_deliveries=p_items)
    assert rec_delay.recommended_plan_id in ["PLAN_A", "PLAN_B", "PLAN_C"]
    assert rec_delay.policy_used == "MINIMIZE_DELAY"
    assert "duration_weight" in rec_delay.criteria_and_weights

    # 3. Test PROTECT_SLA Policy
    rec_sla = engine.evaluate_recommendation(plans, policy="PROTECT_SLA", prioritized_deliveries=p_items)
    assert rec_sla.recommended_plan_id in ["PLAN_A", "PLAN_B", "PLAN_C"]
    assert rec_sla.policy_used == "PROTECT_SLA"
    assert rec_sla.criteria_and_weights["sla_weight"] == 0.60

def test_unavailable_metrics_handling():
    engine = DecisionSupportEngine()
    empty_rec = engine.evaluate_recommendation(recovery_plans={}, policy="MINIMIZE_COST")
    assert empty_rec.recommended_plan_id is None
    assert "No recovery plans available to compare." in empty_rec.reasons

def test_compare_recovery_plans_api_endpoint():
    # 1. Trigger disruption analysis first
    disr_payload = {
        "disruption_id": "DISR_DECISION_API_01",
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge",
        "severity_level": 4.5
    }
    client.post("/api/disruption/analyze", json=disr_payload, headers=headers)

    # 2. Call compare endpoint
    compare_payload = {
        "disruption_id": "DISR_DECISION_API_01",
        "policy": "PROTECT_SLA"
    }
    resp = client.post("/api/recovery/compare", json=compare_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["disruption_id"] == "DISR_DECISION_API_01"
    assert data["policy_used"] == "PROTECT_SLA"
    assert "PLAN_A" in data["plans_comparison"]
    assert "PLAN_B" in data["plans_comparison"]
    assert "PLAN_C" in data["plans_comparison"]
    assert data["recommendation"]["recommended_plan_id"] is not None

    # Verify recommendation DB audit trail without automatic acceptance
    repo = DatabaseRepository()
    db_rec = repo.get_latest_recommendation("DISR_DECISION_API_01")
    assert db_rec is not None
    assert db_rec["policy_used"] == "PROTECT_SLA"

    # Confirm proposal did NOT automatically accept the plan
    latest_sel = repo.get_latest_plan_selection("DISR_DECISION_API_01")
    assert latest_sel is None

def test_cost_metric_sanitization_for_non_operators():
    # Login as delivery_team
    unauth_client = TestClient(app)
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    compare_payload = {
        "disruption_id": "DISR_DECISION_API_01",
        "policy": "MINIMIZE_COST"
    }
    resp = unauth_client.post("/api/recovery/compare", json=compare_payload, headers=d_headers)
    assert resp.status_code == 200
    data = resp.json()

    # Cost metrics should be sanitized / None for non-operator role
    for p_key, plan_comp in data["plans_comparison"].items():
        assert plan_comp["estimated_operating_cost_usd"] is None
