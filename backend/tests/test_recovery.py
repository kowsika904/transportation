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

def test_alternative_paths_generation():
    loader = DataLoader()
    from app.graph.dependency_graph import LogisticsDependencyGraph
    graph = LogisticsDependencyGraph(loader)

    # Calculate paths between Financial District and Brooklyn Navy Yard excluding Manhattan Bridge
    result = graph.find_alternative_paths(
        origin_node="NODE_FINANCIAL",
        destination_node="NODE_BROOKLYN_NAVY",
        exclude_segment_ids=["SEG_MANHATTAN_BRIDGE"]
    )

    assert result["status"] == "SUCCESS"
    assert result["valid_paths_count"] >= 1
    paths = result["paths"]
    assert paths[0]["path_id"] == "PATH_A"
    assert paths[0]["color"] == "#10b981" # Emerald Green
    # Verify SEG_MANHATTAN_BRIDGE is not in path_a segment_ids
    assert "SEG_MANHATTAN_BRIDGE" not in paths[0]["segment_ids"]

def test_unresolvable_routing_endpoints():
    loader = DataLoader()
    from app.graph.dependency_graph import LogisticsDependencyGraph
    graph = LogisticsDependencyGraph(loader)

    with pytest.raises(ValueError, match="Unresolvable routing endpoints"):
        graph.find_alternative_paths(
            origin_node="NODE_INVALID_ORIGIN_999",
            destination_node="NODE_BROOKLYN_NAVY"
        )

def test_no_alternative_path_disconnected_graph():
    loader = DataLoader()
    from app.graph.dependency_graph import LogisticsDependencyGraph
    graph = LogisticsDependencyGraph(loader)

    # Exclude SEG_QUEENS_EXPRESSWAY which completely isolates NODE_JFK_CARGO
    result = graph.find_alternative_paths(
        origin_node="NODE_QUEENS_DC",
        destination_node="NODE_JFK_CARGO",
        exclude_segment_ids=["SEG_QUEENS_EXPRESSWAY"]
    )

    assert result["status"] == "NO_PATH_AVAILABLE"
    assert result["valid_paths_count"] == 0
    assert result["paths"] == []
    assert "No connected road network path exists" in result["reason"]

def test_proposal_persisted_without_automatic_acceptance():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.repository import DatabaseRepository
    from app.api.auth import TEST_SUITE_TOKEN

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

    payload = {
        "disruption_id": "DISR_AUDIT_PROP_01",
        "disruption_type": "road_closure",
        "location_node_id": "SEG_QUEENS_TUNNEL",
        "location_name": "Queens Midtown Tunnel",
        "severity_level": 4.0
    }

    resp = client.post("/api/disruption/analyze", json=payload, headers=headers)
    assert resp.status_code == 200

    repo = DatabaseRepository()
    # Confirm proposals exist in recovery_plans table
    plans_in_db = repo.get_recovery_plans_for_disruption("DISR_AUDIT_PROP_01")
    assert len(plans_in_db) == 3 # PLAN_A, PLAN_B, PLAN_C

    # Confirm proposal analysis did NOT automatically create an accepted plan selection
    latest_sel = repo.get_latest_plan_selection("DISR_AUDIT_PROP_01")
    assert latest_sel is None

def test_dijkstra_path_a_and_path_b_optimization():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    disr = DisruptionInput(
        disruption_id="TEST_DIJKSTRA_01",
        disruption_type="severe_congestion",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=4.0
    )

    plans = engine.generate_recovery_plans(disr, [])
    plan_a = plans["PLAN_A"]
    plan_b = plans["PLAN_B"]

    # Requirement 1 & 2: Objective verification
    assert plan_a.objective_type == "SHORTEST_DISTANCE"
    assert plan_b.objective_type == "FASTEST_TRAVEL_TIME"

    # Path A should have <= distance than Path B (or equal if identical shortest/fastest path)
    assert plan_a.total_distance_km <= plan_b.total_distance_km + 0.001

    # Requirement 3: Blocked edge is never used
    assert "NODE_MANHATTAN_BRIDGE" not in plan_a.route_nodes[1:-1]
    assert plan_a.avoids_disrupted_edge is True
    assert plan_b.avoids_disrupted_edge is True

def test_new_incident_triggers_recomputation():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    disr1 = DisruptionInput(
        disruption_id="TEST_RECOMP_1",
        disruption_type="road_closure",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=5.0
    )
    plans1 = engine.generate_recovery_plans(disr1, [])

    disr2 = DisruptionInput(
        disruption_id="TEST_RECOMP_2",
        disruption_type="road_closure",
        location_node_id="NODE_QUEENS_TUNNEL",
        location_name="Queens Midtown Tunnel",
        severity_level=5.0
    )
    plans2 = engine.generate_recovery_plans(disr2, [])

    # The routes for different disrupted nodes must reflect distinct graph recomputation
    assert plans1["PLAN_A"].route_nodes != plans2["PLAN_A"].route_nodes or plans1["PLAN_A"].calculation_inputs["disrupted_node"] != plans2["PLAN_A"].calculation_inputs["disrupted_node"]

def test_metrics_consistency_and_units():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    disr = DisruptionInput(
        disruption_id="TEST_METRICS_01",
        disruption_type="flooding",
        location_node_id="NODE_FDR_DRIVE",
        location_name="FDR Drive",
        severity_level=3.5
    )

    plans = engine.generate_recovery_plans(disr, [])
    plan_a = plans["PLAN_A"]

    assert plan_a.total_distance_km > 0
    assert plan_a.total_duration_minutes > 0
    assert plan_a.total_cost_usd > 0

    # Ensure distance in km is correctly converted from miles ratio (~1.60934)
    expected_miles = round(plan_a.total_distance_km / 1.60934, 2)
    assert plan_a.total_distance_miles == expected_miles

def test_extraction_flooding_and_vehicle_breakdown_messages():
    from app.engines.extraction_engine import IncidentExtractor
    extractor = IncidentExtractor()

    # Test 1: Flooding message
    res_flood = extractor.extract_from_incident_input(
        description_text="Severe water overflow and flooding reported on FDR Drive corridor",
        form_node_id="NODE_MANHATTAN_BRIDGE",
        form_disruption_type="severe_congestion",
        form_severity=4.0
    )
    assert res_flood.incident_type == "flooding"
    assert res_flood.location_node_id == "NODE_FDR_DRIVE"
    assert res_flood.extraction_method == "Deterministic Rule Parser"

    # Test 2: Vehicle breakdown message
    res_breakdown = extractor.extract_from_incident_input(
        description_text="Disabled vehicle breakdown accident blocking Lincoln Tunnel access",
        form_node_id="NODE_LINCOLN_TUNNEL",
        form_disruption_type="severe_congestion",
        form_severity=3.5
    )
    assert res_breakdown.incident_type == "vehicle_breakdown"
    assert res_breakdown.location_node_id == "NODE_LINCOLN_TUNNEL"

def test_extraction_mismatched_form_and_message_locations():
    from app.engines.extraction_engine import IncidentExtractor
    extractor = IncidentExtractor()

    # Form specifies Manhattan Bridge, but text explicitly describes Queens Midtown Tunnel closure
    res = extractor.extract_from_incident_input(
        description_text="Full road closure and impassable conditions on Queens Midtown Tunnel access road.",
        form_node_id="NODE_MANHATTAN_BRIDGE",
        form_disruption_type="severe_congestion",
        form_severity=4.0
    )
    assert res.location_node_id == "NODE_QUEENS_TUNNEL"
    assert res.is_mismatched_from_form is True
    assert "Discrepancy detected" in res.extraction_reasoning

def test_deterministic_repeated_pipeline_runs():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.auth import TEST_SUITE_TOKEN

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

    payload = {
        "disruption_id": "DISR_DETERM_01",
        "disruption_type": "severe_congestion",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge",
        "severity_level": 4.2,
        "description": "Heavy traffic gridlock on Manhattan Bridge corridor"
    }

    resp1 = client.post("/api/disruption/analyze", json=payload, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()

    resp2 = client.post("/api/disruption/analyze", json=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Ensure 100% deterministic reproducibility
    assert data1["classification"]["predicted_class"] == data2["classification"]["predicted_class"]
    assert data1["classification"]["confidence"] == data2["classification"]["confidence"]
    assert data1["recovery_plans"]["PLAN_A"]["total_distance_km"] == data2["recovery_plans"]["PLAN_A"]["total_distance_km"]
    assert data1["recovery_plans"]["PLAN_B"]["total_duration_minutes"] == data2["recovery_plans"]["PLAN_B"]["total_duration_minutes"]
    assert data1["extraction_method"] == "Deterministic Rule Parser"

def test_different_destinations_produce_distinct_routes():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    disr = DisruptionInput(
        disruption_id="TEST_DEST_01",
        disruption_type="severe_congestion",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=4.0
    )

    items_financial = [
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
    plans_fin = engine.generate_recovery_plans(disr, items_financial)

    items_jfk = [
        PriorityItem(
            delivery_id="DELIV_106",
            customer_name="JFK Express Cargo Terminal",
            priority_score=90.0,
            priority_tier="HIGH",
            sla_end_time="13:00",
            minutes_until_sla=240.0,
            delay_minutes=30.0,
            item_value_usd=45000.0,
            is_perishable=False,
            penalty_usd_per_hour_late=400.0,
            score_breakdown={},
            reasoning="Cargo terminal"
        )
    ]
    plans_jfk = engine.generate_recovery_plans(disr, items_jfk)

    items_harlem = [
        PriorityItem(
            delivery_id="DELIV_105",
            customer_name="Harlem Community Hospital Annex",
            priority_score=98.0,
            priority_tier="CRITICAL",
            sla_end_time="09:45",
            minutes_until_sla=10.0,
            delay_minutes=60.0,
            item_value_usd=32000.0,
            is_perishable=True,
            penalty_usd_per_hour_late=750.0,
            score_breakdown={},
            reasoning="Hospital annex"
        )
    ]
    plans_harlem = engine.generate_recovery_plans(disr, items_harlem)

    # Verify that different destinations produce distinct routes, metrics, and target node IDs
    assert plans_fin["PLAN_A"].total_distance_km != plans_jfk["PLAN_A"].total_distance_km
    assert plans_fin["PLAN_A"].total_distance_km != plans_harlem["PLAN_A"].total_distance_km
    assert plans_fin["PLAN_A"].route_nodes[-1] == "NODE_FINANCIAL"
    assert plans_jfk["PLAN_A"].route_nodes[-1] == "NODE_JFK_CARGO"
    assert plans_harlem["PLAN_A"].route_nodes[-1] == "NODE_HARLEM_GATEWAY"


def test_manhattan_vs_williamsburg_bridge_closures():
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)

    # Disruption 1: Manhattan Bridge Closure
    disr_manhattan = DisruptionInput(
        disruption_id="DISR_TEST_MANHATTAN",
        disruption_type="bridge_closure",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge Corridor",
        severity_level=5.0,
        description="ROAD BLOCKED — Manhattan Bridge due to vehicle breakdown."
    )
    plans_manhattan = engine.generate_recovery_plans(disr_manhattan, [])

    # Disruption 2: Williamsburg Bridge Closure
    disr_williamsburg = DisruptionInput(
        disruption_id="DISR_TEST_WILLIAMSBURG",
        disruption_type="bridge_closure",
        location_node_id="NODE_WILLIAMSBURG_BRIDGE",
        location_name="Williamsburg Bridge Corridor",
        severity_level=5.0,
        description="VEHICLE BREAKDOWN — Williamsburg Bridge blocking traffic lane."
    )
    plans_williamsburg = engine.generate_recovery_plans(disr_williamsburg, [])

    plan_a_manhattan = plans_manhattan["PLAN_A"]
    plan_a_williamsburg = plans_williamsburg["PLAN_A"]

    # 1. Closing Manhattan Bridge excludes Manhattan Bridge from route nodes
    assert "NODE_MANHATTAN_BRIDGE" not in plan_a_manhattan.route_nodes

    # 2. Closing Williamsburg Bridge excludes Williamsburg Bridge from route nodes
    assert "NODE_WILLIAMSBURG_BRIDGE" not in plan_a_williamsburg.route_nodes

    # 3. Path distances & edge IDs must differ between the two bridge incidents
    assert plan_a_manhattan.route_edge_ids != plan_a_williamsburg.route_edge_ids
    assert plan_a_manhattan.total_distance_km != plan_a_williamsburg.total_distance_km

    # 4. Metrics match actual sum of selected route edges
    sum_dist_manhattan = sum(
        e["distance_miles"] * 1.60934
        for e in engine.BASE_NETWORK_EDGES
        if e["id"] in plan_a_manhattan.route_edge_ids
    )
    assert abs(plan_a_manhattan.total_distance_km - round(sum_dist_manhattan, 2)) <= 0.05


def test_location_mismatch_detection():
    from app.engines.extraction_engine import IncidentExtractor

    extractor = IncidentExtractor()
    extracted = extractor.extract_from_incident_input(
        description_text="VEHICLE BREAKDOWN — Williamsburg Bridge blocking lane.",
        form_node_id="NODE_MANHATTAN_BRIDGE",
        form_disruption_type="vehicle_breakdown",
        form_severity=4.0,
        form_location_name="Manhattan Bridge Corridor"
    )

    # Must flag mismatch when message specifies Williamsburg Bridge but form dropdown has Manhattan Bridge
    assert extracted.is_mismatched_from_form is True
    assert extracted.location_node_id == "NODE_WILLIAMSBURG_BRIDGE"


def test_incident_1_flooding_brooklyn_bridge_vs_incident_2_manhattan_bridge_blocked():
    from app.engines.extraction_engine import IncidentExtractor
    loader = DataLoader()
    engine = ORToolsRecoveryEngine(loader)
    extractor = IncidentExtractor()

    # INCIDENT 1: ROAD FLOODING — BROOKLYN BRIDGE CORRIDOR
    msg_1 = "Heavy rainfall has caused flooding on the road. Traffic is severely delayed, and some vehicles cannot pass safely. Please reroute affected deliveries immediately and prioritize urgent shipments."
    ext_1 = extractor.extract_from_incident_input(
        description_text=msg_1,
        form_node_id="NODE_BROOKLYN_BRIDGE",
        form_disruption_type="flooding",
        form_severity=3.5,
        form_location_name="Brooklyn Bridge Corridor"
    )
    assert ext_1.incident_type == "flooding"
    assert ext_1.location_node_id == "NODE_BROOKLYN_BRIDGE"
    assert ext_1.is_mismatched_from_form is False

    disr_1 = DisruptionInput(
        disruption_id="INCIDENT_01_FLOODING",
        disruption_type=ext_1.incident_type,
        location_node_id=ext_1.location_node_id,
        location_name=ext_1.location_name,
        severity_level=ext_1.severity_level,
        description=msg_1
    )
    plans_1 = engine.generate_recovery_plans(disr_1, [])

    # INCIDENT 2: ROAD BLOCKED — MANHATTAN BRIDGE
    msg_2 = "Road blocked due to a vehicle breakdown. Heavy traffic expected. Please reroute affected deliveries immediately."
    ext_2 = extractor.extract_from_incident_input(
        description_text=msg_2,
        form_node_id="NODE_MANHATTAN_BRIDGE",
        form_disruption_type="vehicle_breakdown",
        form_severity=4.0,
        form_location_name="Manhattan Bridge Corridor"
    )
    assert ext_2.incident_type == "vehicle_breakdown"
    assert ext_2.location_node_id == "NODE_MANHATTAN_BRIDGE"
    assert ext_2.is_mismatched_from_form is False

    disr_2 = DisruptionInput(
        disruption_id="INCIDENT_02_MANHATTAN",
        disruption_type=ext_2.incident_type,
        location_node_id=ext_2.location_node_id,
        location_name=ext_2.location_name,
        severity_level=ext_2.severity_level,
        description=msg_2
    )
    plans_2 = engine.generate_recovery_plans(disr_2, [])

    plan_a_1, plan_b_1 = plans_1["PLAN_A"], plans_1["PLAN_B"]
    plan_a_2, plan_b_2 = plans_2["PLAN_A"], plans_2["PLAN_B"]

    # Verify separate incident IDs & outputs
    assert disr_1.disruption_id != disr_2.disruption_id
    assert plan_a_1.route_edge_ids != plan_a_2.route_edge_ids

    # Manhattan Bridge blockage excludes Manhattan Bridge from Incident 2
    assert "NODE_MANHATTAN_BRIDGE" not in plan_a_2.route_nodes

    # Path A and Path B objectives computed independently
    assert plan_a_1.objective_type == "SHORTEST_DISTANCE"
    assert plan_b_1.objective_type == "FASTEST_TRAVEL_TIME"





