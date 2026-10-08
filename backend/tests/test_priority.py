import pytest
from app.data.loader import DataLoader
from app.engines.priority_engine import PriorityEngine
from app.models.schemas import AffectedDelivery

def test_priority_engine_scoring():
    loader = DataLoader()
    engine = PriorityEngine(loader)

    mock_deliveries = [
        AffectedDelivery(
            delivery_id="DELIV_101",
            customer_id="CUST_101",
            customer_name="Apex Medical Supplies Hub",
            route_id="ROUTE_A",
            assigned_vehicle_id="VEH_01",
            original_eta="09:15",
            projected_eta="11:45",
            delay_minutes=150.0,
            sla_window_end="10:30",
            sla_violated=True,
            priority_score=0.0,
            item_value_usd=25000.0,
            is_perishable=True
        ),
        AffectedDelivery(
            delivery_id="DELIV_104",
            customer_id="CUST_104",
            customer_name="East Side Electronics Outlets",
            route_id="ROUTE_B",
            assigned_vehicle_id="VEH_02",
            original_eta="09:30",
            projected_eta="10:00",
            delay_minutes=30.0,
            sla_window_end="12:00",
            sla_violated=False,
            priority_score=0.0,
            item_value_usd=18000.0,
            is_perishable=False
        )
    ]

    ranked = engine.rank_affected_deliveries(mock_deliveries)
    assert len(ranked) == 2
    # Critical medical delivery should be ranked first
    assert ranked[0].delivery_id == "DELIV_101"
    assert ranked[0].priority_score > ranked[1].priority_score
    assert ranked[0].priority_tier == "CRITICAL"
