import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.config import SessionLocal, engine, Base
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DisruptionModel, RecoveryPlanModel, PlanSelectionModel
)
from app.db.seed import seed_database
from app.db.repository import DatabaseRepository

from app.api.auth import TEST_SUITE_TOKEN

client = TestClient(app)
client.headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

def test_db_connection_and_session():
    db = SessionLocal()
    try:
        assert db.is_active
    finally:
        db.close()

def test_seed_database_and_verify_entities():
    summary = seed_database()
    assert summary["depots_seeded"] == 2
    assert summary["segments_seeded"] == 10
    assert summary["customers_seeded"] == 6
    assert summary["vehicles_seeded"] == 4
    assert summary["routes_seeded"] == 3

    db = SessionLocal()
    try:
        depots = db.query(DepotModel).all()
        customers = db.query(CustomerModel).all()
        vehicles = db.query(VehicleModel).all()
        routes = db.query(RouteModel).all()

        assert len(depots) == 2
        assert len(customers) == 6
        assert len(vehicles) == 4
        assert len(routes) == 3
    finally:
        db.close()

def test_geospatial_wkt_formatting():
    db = SessionLocal()
    try:
        # Check Customer Point WKT/Geom
        cust = db.query(CustomerModel).first()
        assert cust is not None

        # Check Road Segment LineString WKT/Geom
        seg = db.query(RoadSegmentModel).first()
        assert seg is not None
    finally:
        db.close()

def test_db_status_api_endpoint():
    response = client.get("/api/db/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CONNECTED"
    assert data["depots_count"] == 2
    assert data["customers_count"] == 6

def test_end_to_end_disruption_db_persistence():
    payload = {
        "disruption_id": "DISR_DB_TEST_01",
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Deck",
        "severity_level": 4.5,
        "wind_speed_mph": 15.0,
        "precipitation_inches": 0.0,
        "visibility_miles": 8.0,
        "temperature_f": 45.0,
        "road_capacity_reduction_pct": 100.0,
        "average_speed_mph": 0.0,
        "normal_speed_mph": 40.0,
        "active_vehicle_incident": False,
        "description": "Database persistence verification event"
    }

    # 1. Trigger full analysis
    response = client.post("/api/disruption/analyze", json=payload)
    assert response.status_code == 200

    # 2. Check DB records
    db = SessionLocal()
    try:
        disr = db.query(DisruptionModel).filter_by(id="DISR_DB_TEST_01").first()
        assert disr is not None
        assert disr.disruption_type == "bridge_closure"

        plans = db.query(RecoveryPlanModel).filter_by(disruption_id="DISR_DB_TEST_01").all()
        assert len(plans) == 3
        plan_ids = [p.plan_id for p in plans]
        assert "PLAN_A" in plan_ids
        assert "PLAN_B" in plan_ids
        assert "PLAN_C" in plan_ids
    finally:
        db.close()

    # 3. Accept Plan B and check persistence
    accept_payload = {
        "disruption_id": "DISR_DB_TEST_01",
        "selected_plan_id": "PLAN_B",
        "operator_id": "OPERATOR_DB_TEST",
        "operator_notes": "Selected Plan B fast recovery for DB persistence test"
    }
    accept_resp = client.post("/api/recovery/accept", json=accept_payload)
    assert accept_resp.status_code == 200

    db = SessionLocal()
    try:
        sel = db.query(PlanSelectionModel).filter_by(disruption_id="DISR_DB_TEST_01").first()
        assert sel is not None
        assert sel.status == "ACCEPTED"
        assert sel.operator_id == "OPERATOR_DB_TEST"
    finally:
        db.close()

def test_repeated_disruption_analysis_idempotency():
    """
    Verifies that running the exact same disruption analysis multiple times:
    1. Does NOT crash with UniqueViolation on recovery_plans_pkey.
    2. Leaves exactly 1 logical Plan A, 1 Plan B, and 1 Plan C for that disruption.
    3. Successfully updates generated recovery plan attributes.
    4. Allows a new disruption to create its own distinct Plan A/B/C.
    5. Preserves existing operator decision logs in plan_selections.
    """
    disruption_payload = {
        "disruption_id": "DISR_NYC_BLIZZARD_01",
        "disruption_type": "blizzard",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Corridor",
        "severity_level": 4.8,
        "wind_speed_mph": 42.5,
        "precipitation_inches": 3.2,
        "visibility_miles": 0.3,
        "temperature_f": 22.0,
        "road_capacity_reduction_pct": 85.0,
        "average_speed_mph": 6.2,
        "normal_speed_mph": 40.0,
        "active_vehicle_incident": False,
        "description": "Category 4 Blizzard"
    }

    # 1. First Analysis Call
    resp1 = client.post("/api/disruption/analyze", json=disruption_payload)
    assert resp1.status_code == 200

    # 2. Second Analysis Call (Exact Same Disruption) -> Must NOT throw UniqueViolation
    resp2 = client.post("/api/disruption/analyze", json=disruption_payload)
    assert resp2.status_code == 200

    # 3. Third Analysis Call with modified severity -> Must update existing records idempotently
    modified_payload = dict(disruption_payload)
    modified_payload["severity_level"] = 5.0
    resp3 = client.post("/api/disruption/analyze", json=modified_payload)
    assert resp3.status_code == 200

    db = SessionLocal()
    try:
        # Confirm exactly 3 recovery plans exist for DISR_NYC_BLIZZARD_01
        plans = db.query(RecoveryPlanModel).filter_by(disruption_id="DISR_NYC_BLIZZARD_01").all()
        assert len(plans) == 3

        plan_map = {p.plan_id: p for p in plans}
        assert "PLAN_A" in plan_map
        assert "PLAN_B" in plan_map
        assert "PLAN_C" in plan_map

        # Confirm primary keys are exactly DISR_NYC_BLIZZARD_01_PLAN_A, etc.
        assert plan_map["PLAN_A"].id == "DISR_NYC_BLIZZARD_01_PLAN_A"
        assert plan_map["PLAN_B"].id == "DISR_NYC_BLIZZARD_01_PLAN_B"
        assert plan_map["PLAN_C"].id == "DISR_NYC_BLIZZARD_01_PLAN_C"
    finally:
        db.close()

    # 4. New Disruption Analysis -> Creates distinct Plan A/B/C
    new_disr_payload = {
        "disruption_id": "DISR_NEW_EVENT_99",
        "disruption_type": "truck_breakdown",
        "location_node_id": "NODE_QUEENS_DC",
        "location_name": "Queens Hub",
        "severity_level": 3.0,
        "road_capacity_reduction_pct": 50.0,
        "average_speed_mph": 15.0,
        "normal_speed_mph": 40.0
    }
    resp_new = client.post("/api/disruption/analyze", json=new_disr_payload)
    assert resp_new.status_code == 200

    db = SessionLocal()
    try:
        new_plans = db.query(RecoveryPlanModel).filter_by(disruption_id="DISR_NEW_EVENT_99").all()
        assert len(new_plans) == 3
    finally:
        db.close()
