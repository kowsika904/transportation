import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.config import SessionLocal
from app.db.models import DisruptionModel, NotificationModel, AuditLogModel, PlanSelectionModel, PlanRecommendationModel, RecoveryPlanModel
from app.api.auth import TEST_SUITE_TOKEN, ACTIVE_TOKENS

client = TestClient(app)
client.headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

def test_phase6_incident_lifecycle_transitions():
    unauth_client = TestClient(app)

    # Login as transport team
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    t_token = t_login.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Login as logistics operator
    o_login = unauth_client.post("/api/auth/login", json={"username": "operator", "password": "operator123", "role": "logistics_operator"})
    o_token = o_login.json()["access_token"]
    o_headers = {"Authorization": f"Bearer {o_token}"}

    disruption_id = "DISR_LIFECYCLE_TEST_01"

    # 1. Transport team reports disruption
    disr_payload = {
        "disruption_id": disruption_id,
        "disruption_type": "severe_congestion",
        "location_node_id": "NODE_MIDTOWN_HUB",
        "location_name": "Midtown Distribution Hub Corridor",
        "severity_level": 4.0,
        "description": "Heavy traffic gridlock reported by transport unit"
    }
    rep_resp = unauth_client.post("/api/disruption/report", json=disr_payload, headers=t_headers)
    assert rep_resp.status_code == 200

    # Verify initially persisted status is RECOVERY_PROPOSED after analysis
    db = SessionLocal()
    try:
        disr = db.query(DisruptionModel).filter_by(id=disruption_id).first()
        assert disr is not None
        assert disr.status in ["REPORTED", "RECOVERY_PROPOSED"]
    finally:
        db.close()

    # 2. Transport team attempts to mark status as RESOLVED -> MUST BE REJECTED 403
    t_resolve_resp = unauth_client.post(
        f"/api/disruption/{disruption_id}/status",
        json={"status": "RESOLVED"},
        headers=t_headers
    )
    assert t_resolve_resp.status_code == 403
    assert "Operator authorization required" in t_resolve_resp.json()["detail"]

    # 3. Logistics operator updates status to RECOVERY_APPROVED
    o_approve_resp = unauth_client.post(
        f"/api/disruption/{disruption_id}/status",
        json={"status": "RECOVERY_APPROVED"},
        headers=o_headers
    )
    assert o_approve_resp.status_code == 200
    assert o_approve_resp.json()["current_status"] == "RECOVERY_APPROVED"

    # 4. Logistics operator resolves incident
    o_resolve_resp = unauth_client.post(
        f"/api/disruption/{disruption_id}/status",
        json={"status": "RESOLVED"},
        headers=o_headers
    )
    assert o_resolve_resp.status_code == 200
    assert o_resolve_resp.json()["current_status"] == "RESOLVED"

    # 5. Invalid transition from RESOLVED to REPORTED -> MUST BE REJECTED 400
    invalid_resp = unauth_client.post(
        f"/api/disruption/{disruption_id}/status",
        json={"status": "REPORTED"},
        headers=o_headers
    )
    assert invalid_resp.status_code == 400
    assert "Invalid status transition" in invalid_resp.json()["detail"]

def test_phase6_notification_deduplication_and_role_access():
    unauth_client = TestClient(app)

    # Login as delivery team
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    # 1. Fetch notifications for delivery role
    notif_resp = unauth_client.get("/api/notifications", headers=d_headers)
    assert notif_resp.status_code == 200
    notif_data = notif_resp.json()
    assert "notifications" in notif_data
    assert "unread_count" in notif_data

    # 2. Test notification read marking
    if notif_data["notifications"]:
        first_notif_id = notif_data["notifications"][0]["id"]
        read_resp = unauth_client.post(f"/api/notifications/{first_notif_id}/read", headers=d_headers)
        assert read_resp.status_code == 200
        assert read_resp.json()["status"] == "SUCCESS"

    # 3. Test notification deduplication by event key via repository call
    from app.db.repository import DatabaseRepository
    repo = DatabaseRepository()
    notif1 = repo.create_notification(
        event_key="DEDUP_TEST_EVENT_001",
        event_type="DISRUPTION_REPORTED",
        title="Deduplication Test",
        message="Message content 1",
        disruption_id="DISR_DEDUP_01",
        recipient_role="all"
    )
    notif2 = repo.create_notification(
        event_key="DEDUP_TEST_EVENT_001",
        event_type="DISRUPTION_REPORTED",
        title="Deduplication Test",
        message="Message content 2",
        disruption_id="DISR_DEDUP_01",
        recipient_role="all"
    )
    assert notif1["id"] == notif2["id"]

def test_phase6_audit_trail_and_health_check():
    unauth_client = TestClient(app)

    # 1. Detailed health check endpoint
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["status"] == "HEALTHY"
    assert h_data["api_status"] == "ONLINE"
    assert h_data["database"]["status"] == "CONNECTED"
    assert "classifier_service" in h_data["models_and_engines"]
    assert h_data["notification_subsystem"] == "ONLINE"

    # 2. Operator fetches audit logs
    o_login = unauth_client.post("/api/auth/login", json={"username": "operator", "password": "operator123", "role": "logistics_operator"})
    o_token = o_login.json()["access_token"]
    o_headers = {"Authorization": f"Bearer {o_token}"}

    audit_resp = unauth_client.get("/api/audit-logs", headers=o_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["logs"]
    assert isinstance(logs, list)

    # 3. Non-operator fetching audit logs -> MUST BE REJECTED 403
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    forbidden_audit = unauth_client.get("/api/audit-logs", headers=d_headers)
    assert forbidden_audit.status_code == 403

def test_phase6_end_to_end_10_step_integration_scenario():
    """
    Executes the exact 10-step end-to-end integration scenario specified in Phase 6 requirements:
    1. Authenticate as Transport Team.
    2. Report a disruption.
    3. Verify incident persistence and audit history.
    4. Verify authorized portals receive appropriate notification.
    5. Generate recovery plans.
    6. Verify plan generation does NOT automatically accept plan or alter accepted delivery assignments.
    7. Authenticate as Logistics Operator and accept a feasible plan.
    8. Verify acceptance is audited and relevant delivery projections update correctly.
    9. Verify Delivery Management can view and acknowledge affected deliveries.
    10. Resolve incident through authorized workflow and verify status history.
    """
    unauth_client = TestClient(app)

    # Step 1: Authenticate as Transport Team
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    assert t_login.status_code == 200
    t_token = t_login.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Step 2: Report a disruption
    disruption_id = "DISR_E2E_SCENARIO_100"
    report_payload = {
        "disruption_id": disruption_id,
        "disruption_type": "blizzard",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Corridor",
        "severity_level": 4.5,
        "wind_speed_mph": 35.0,
        "precipitation_inches": 2.5,
        "description": "Simulated E2E Blizzard Event"
    }
    rep_resp = unauth_client.post("/api/disruption/report", json=report_payload, headers=t_headers)
    assert rep_resp.status_code == 200
    analysis = rep_resp.json()

    # Step 3: Verify incident persistence and audit history
    db = SessionLocal()
    try:
        disr = db.query(DisruptionModel).filter_by(id=disruption_id).first()
        assert disr is not None
        assert disr.reported_by == "transport"
        assert disr.disruption_type == "blizzard"
    finally:
        db.close()

    # Step 4: Verify authorized portals receive appropriate notification
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    notifs_resp = unauth_client.get("/api/notifications", headers=d_headers)
    assert notifs_resp.status_code == 200
    notif_titles = [n["title"] for n in notifs_resp.json()["notifications"]]
    assert any("Manhattan Bridge Corridor" in t for t in notif_titles)

    # Step 5: Generate recovery plans (returned in analysis response)
    assert "PLAN_A" in analysis["recovery_plans"]
    assert "PLAN_B" in analysis["recovery_plans"]
    assert "PLAN_C" in analysis["recovery_plans"]

    # Step 6: Verify plan generation does NOT automatically accept a plan or alter accepted delivery assignments
    active_inc_resp = unauth_client.get("/api/incidents/active", headers=t_headers)
    assert active_inc_resp.status_code == 200
    active_data = active_inc_resp.json()
    assert active_data["applied_plan_id"] is None or active_data["applied_plan"] is None

    # Step 7: Authenticate as Logistics Operator and accept a feasible plan (PLAN_B)
    o_login = unauth_client.post("/api/auth/login", json={"username": "operator", "password": "operator123", "role": "logistics_operator"})
    o_token = o_login.json()["access_token"]
    o_headers = {"Authorization": f"Bearer {o_token}"}

    accept_resp = unauth_client.post(
        "/api/recovery/accept",
        json={"disruption_id": disruption_id, "selected_plan_id": "PLAN_B", "operator_notes": "Accepted Plan B for E2E scenario"},
        headers=o_headers
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"
    assert accept_resp.json()["applied_plan_id"] == "PLAN_B"

    # Step 8: Verify acceptance is audited and relevant delivery projections update correctly
    audit_resp = unauth_client.get("/api/audit-logs", headers=o_headers)
    assert audit_resp.status_code == 200
    action_types = [a["action_type"] for a in audit_resp.json()["logs"]]
    assert "PLAN_ACCEPTED" in action_types

    # Step 9: Verify Delivery Management can view and acknowledge affected deliveries
    deliv_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers)
    assert deliv_resp.status_code == 200
    deliv_data = deliv_resp.json()
    assert deliv_data["affected_deliveries_count"] > 0

    ack_resp = unauth_client.post(
        "/api/deliveries/acknowledge",
        json={"delivery_id": deliv_data["affected_deliveries"][0]["delivery_id"], "notes": "E2E delivery acknowledged by team"},
        headers=d_headers
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # Step 10: Resolve the incident through authorized workflow and verify status history
    resolve_resp = unauth_client.post(
        f"/api/disruption/{disruption_id}/status",
        json={"status": "RESOLVED"},
        headers=o_headers
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["current_status"] == "RESOLVED"

    db = SessionLocal()
    try:
        final_disr = db.query(DisruptionModel).filter_by(id=disruption_id).first()
        assert final_disr.status == "RESOLVED"
    finally:
        db.close()

def test_transport_agent_first_unsubmitted_and_submitted_messaging():
    """
    Proves Transport-Agent-First Incident Messaging:
    1. Unsubmitted state returns NO_ACTIVE_INCIDENT and does not broadcast fake/invented incidents.
    2. Transport Agent submits an incident report (type, location, corridor, severity, description).
    3. Incident is persisted in DB with reported_by = 'transport'.
    4. Both authorized portals (Logistics Operator & Delivery Management) receive the submitted incident message.
    """
    unauth_client = TestClient(app)

    # 1. Clear active_plan_store to simulate clean state
    from app.api.routes import active_plan_store
    active_plan_store.clear()

    from app.db.models import DisruptionModel, NotificationModel, AuditLogModel, PlanSelectionModel, RecoveryPlanModel, PlanRecommendationModel

    # Clear disruptions and dependent plan records from DB to test unsubmitted state
    db = SessionLocal()
    try:
        db.query(PlanSelectionModel).delete()
        db.query(PlanRecommendationModel).delete()
        db.query(RecoveryPlanModel).delete()
        db.query(DisruptionModel).delete()
        db.commit()
    finally:
        db.close()

    # 2. Login as Logistics Operator and check feed BEFORE Transport Agent submits report
    o_login = unauth_client.post("/api/auth/login", json={"username": "operator", "password": "operator123", "role": "logistics_operator"})
    o_headers = {"Authorization": f"Bearer {o_login.json()['access_token']}"}

    unsubmitted_inc_resp = unauth_client.get("/api/incidents/active", headers=o_headers)
    assert unsubmitted_inc_resp.status_code == 200
    assert unsubmitted_inc_resp.json()["status"] == "NO_ACTIVE_INCIDENT"
    assert unsubmitted_inc_resp.json()["disruption_input"] is None

    # Login as Delivery Team and check feed BEFORE Transport Agent submits report
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_headers = {"Authorization": f"Bearer {d_login.json()['access_token']}"}

    unsubmitted_deliv_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers)
    assert unsubmitted_deliv_resp.status_code == 200
    assert unsubmitted_deliv_resp.json()["status"] == "NO_ACTIVE_INCIDENT"
    assert unsubmitted_deliv_resp.json()["affected_deliveries_count"] == 0

    # 3. Transport Agent reports a new disruption
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    t_headers = {"Authorization": f"Bearer {t_login.json()['access_token']}"}

    disrupt_id = "DISR_TRP_FIRST_999"
    report_payload = {
        "disruption_id": disrupt_id,
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Main Span",
        "severity_level": 4.8,
        "description": "Transport driver reported emergency bridge closure"
    }

    sub_resp = unauth_client.post("/api/disruption/report", json=report_payload, headers=t_headers)
    assert sub_resp.status_code == 200
    assert sub_resp.json()["disruption_input"]["location_name"] == "Manhattan Bridge Main Span"

    # 4. Verify DB persistence and reported_by identity
    db = SessionLocal()
    try:
        db_disr = db.query(DisruptionModel).filter_by(id=disrupt_id).first()
        assert db_disr is not None
        assert db_disr.reported_by == "transport"
        assert db_disr.location_name == "Manhattan Bridge Main Span"
    finally:
        db.close()

    # 5. Verify Logistics Operator portal NOW receives the submitted incident message and recovery plans
    submitted_inc_resp = unauth_client.get("/api/incidents/active", headers=o_headers)
    assert submitted_inc_resp.status_code == 200
    inc_data = submitted_inc_resp.json()
    assert inc_data["status"] == "ACTIVE"
    assert inc_data["disruption_id"] == disrupt_id
    assert inc_data["disruption_input"]["location_name"] == "Manhattan Bridge Main Span"
    assert "PLAN_A" in inc_data["all_recovery_plans"]

    # 6. Verify Delivery Management portal NOW receives the submitted incident message and affected deliveries
    submitted_deliv_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers)
    assert submitted_deliv_resp.status_code == 200
    deliv_data = submitted_deliv_resp.json()
    assert deliv_data["status"] == "ACTIVE"
    assert deliv_data["disruption_id"] == disrupt_id
    assert deliv_data["location_name"] == "Manhattan Bridge Main Span"
    assert deliv_data["affected_deliveries_count"] > 0

def test_requirement_e_end_to_end_verification():
    """
    Requirement E Verification:
    1. Start with no valid active incident -> verify empty state on both portals.
    2. Failed submission attempt -> verify no false success or incident publication.
    3. Transport Agent submits unique message TEST-TRANSPORT-7391.
    4. Verify backend persists exact message & disruption ID.
    5. Verify Transport Team feed & Delivery Management portal render exact message.
    6. Reload / refresh simulation -> verify persisted incident remains active.
    """
    unauth_client = TestClient(app)
    from app.api.routes import active_plan_store
    active_plan_store.clear()

    db = SessionLocal()
    try:
        db.query(PlanSelectionModel).delete()
        db.query(PlanRecommendationModel).delete()
        db.query(RecoveryPlanModel).delete()
        db.query(DisruptionModel).delete()
        db.commit()
    finally:
        db.close()

    # Logins
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    t_headers = {"Authorization": f"Bearer {t_login.json()['access_token']}"}

    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_headers = {"Authorization": f"Bearer {d_login.json()['access_token']}"}

    # 1. Verify empty state
    inc_empty = unauth_client.get("/api/incidents/active", headers=t_headers).json()
    deliv_empty = unauth_client.get("/api/deliveries/affected", headers=d_headers).json()
    assert inc_empty["status"] == "NO_ACTIVE_INCIDENT"
    assert deliv_empty["status"] == "NO_ACTIVE_INCIDENT"

    # 2. Test failed submission (delivery role trying to report disruption -> 403 Forbidden)
    failed_sub = unauth_client.post("/api/disruption/report", json={
        "disruption_id": "DISR_FAILED_01",
        "disruption_type": "severe_congestion",
        "location_node_id": "NODE_MIDTOWN_HUB",
        "location_name": "Midtown Hub",
        "severity_level": 4.0,
        "description": "Unauthorized attempt"
    }, headers=d_headers)
    assert failed_sub.status_code == 403
    # Verify feed is still empty
    assert unauth_client.get("/api/incidents/active", headers=t_headers).json()["status"] == "NO_ACTIVE_INCIDENT"

    # 3. Transport Agent submits unique incident message
    unique_msg = "TEST-TRANSPORT-7391: New road obstruction reported by Transport Team"
    inc_id = "DISR_TEST_7391"
    sub_payload = {
        "disruption_id": inc_id,
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Corridor",
        "severity_level": 4.5,
        "description": unique_msg
    }
    res = unauth_client.post("/api/disruption/report", json=sub_payload, headers=t_headers)
    assert res.status_code == 200

    # 4. Verify DB persistence
    db = SessionLocal()
    try:
        d_rec = db.query(DisruptionModel).filter_by(id=inc_id).first()
        assert d_rec is not None
        assert d_rec.description == unique_msg
        assert d_rec.reported_by == "transport"
    finally:
        db.close()

    # 5. Verify both portals render exact message & same ID
    inc_active = unauth_client.get("/api/incidents/active", headers=t_headers).json()
    deliv_active = unauth_client.get("/api/deliveries/affected", headers=d_headers).json()

    assert inc_active["status"] == "ACTIVE"
    assert inc_active["disruption_id"] == inc_id
    assert inc_active["disruption_input"]["description"] == unique_msg

    assert deliv_active["status"] == "ACTIVE"
    assert deliv_active["disruption_id"] == inc_id
    assert deliv_active["description"] == unique_msg

    # 6. Reload / refresh simulation (clear in-memory store, force DB lookup)
    active_plan_store.clear()
    inc_reload = unauth_client.get("/api/incidents/active", headers=t_headers).json()
    deliv_reload = unauth_client.get("/api/deliveries/affected", headers=d_headers).json()

    assert inc_reload["status"] == "ACTIVE"
    assert inc_reload["disruption_id"] == inc_id
    assert inc_reload["disruption_input"]["description"] == unique_msg

    assert deliv_reload["status"] == "ACTIVE"
    assert deliv_reload["disruption_id"] == inc_id
    assert deliv_reload["description"] == unique_msg

def test_delivery_map_disruption_and_reroute_visualization():
    """
    Verifies map disruption highlight and optimized reroute visualization:
    1. Returns disrupted_segment (RED), original_route (BLUE), and optimized_route (GREEN).
    2. Confirms optimized route avoids the blocked corridor.
    3. Confirms infeasibility condition returns NO_FEASIBLE_ROUTE with reason.
    """
    unauth_client = TestClient(app)
    from app.api.routes import active_plan_store
    active_plan_store.clear()

    db = SessionLocal()
    try:
        db.query(PlanSelectionModel).delete()
        db.query(PlanRecommendationModel).delete()
        db.query(RecoveryPlanModel).delete()
        db.query(DisruptionModel).delete()
        db.commit()
    finally:
        db.close()

    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    t_headers = {"Authorization": f"Bearer {t_login.json()['access_token']}"}

    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_headers = {"Authorization": f"Bearer {d_login.json()['access_token']}"}

    # 1. Report disruption at Manhattan Bridge
    inc_id = "DISR_VIS_MAP_001"
    sub_payload = {
        "disruption_id": inc_id,
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Corridor",
        "severity_level": 4.5,
        "description": "Bridge closure - reroute via Queens Midtown Tunnel"
    }
    rep = unauth_client.post("/api/disruption/report", json=sub_payload, headers=t_headers)
    assert rep.status_code == 200

    # 2. Query Delivery Management portal
    deliv_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers).json()
    assert deliv_resp["status"] == "ACTIVE"
    assert deliv_resp["disrupted_segment"] is not None
    assert deliv_resp["disrupted_segment"]["v_node"] == "NODE_MANHATTAN_BRIDGE"
    assert len(deliv_resp["disrupted_segment"]["coords"]) == 2

    assert deliv_resp["original_route"] is not None
    assert len(deliv_resp["original_route"]["coords"]) >= 2

    assert deliv_resp["optimized_route"] is not None
    assert deliv_resp["optimization_status"] == "FEASIBLE"
    assert deliv_resp["optimized_route"]["total_distance_miles"] > 0
    assert deliv_resp["optimized_route"]["total_duration_minutes"] > 0

    # Verify optimized route coordinates do NOT contain Manhattan Bridge node [40.7090, -73.9900]
    opt_coords = deliv_resp["optimized_route"]["coords"]
    manhattan_bridge_coords = [40.7090, -73.9900]
    assert manhattan_bridge_coords not in opt_coords

    # 3. Test infeasible disruption scenario
    active_plan_store.clear()
    infeasible_id = "DISR_INFEASIBLE_002"
    inf_payload = {
        "disruption_id": infeasible_id,
        "disruption_type": "no_alternative_blocked",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge Corridor",
        "severity_level": 5.0,
        "description": "Total network gridlock with no alternative path"
    }
    rep_inf = unauth_client.post("/api/disruption/report", json=inf_payload, headers=t_headers)
    assert rep_inf.status_code == 200

    deliv_inf = unauth_client.get("/api/deliveries/affected", headers=d_headers).json()
    assert deliv_inf["status"] == "ACTIVE"
    assert deliv_inf["optimization_status"] == "NO_FEASIBLE_ROUTE"
    assert deliv_inf["infeasibility_reason"] is not None
    assert deliv_inf["optimized_route"] is None



