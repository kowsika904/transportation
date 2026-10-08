import pytest
from app.data.loader import DataLoader
from app.engines.recovery_engine import ORToolsRecoveryEngine
from app.models.schemas import DisruptionInput, PriorityItem

def test_ortools_recovery_plan_generation():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    disr = DisruptionInput(
        disruption_id="TEST_RECOVERY",
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
            reasoning="Medical critical"
        )
    ]

    plans = engine.generate_recovery_plans(disr, p_items)
    assert "PLAN_A" in plans
    assert "PLAN_B" in plans
    assert "PLAN_C" in plans

    assert plans["PLAN_A"].plan_id == "PLAN_A"
    assert plans["PLAN_B"].plan_id == "PLAN_B"
    assert plans["PLAN_C"].plan_id == "PLAN_C"

    # Verify each plan has valid route details and trade offs
    assert len(plans["PLAN_A"].vehicle_routes) > 0
    assert len(plans["PLAN_B"].trade_offs) > 0
    assert len(plans["PLAN_C"].rule_reasons) > 0
