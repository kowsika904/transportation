import pytest
from fastapi.testclient import TestClient
from app.main import app

from app.api.auth import TEST_SUITE_TOKEN

client = TestClient(app)
client.headers = {"Authorization": f"Bearer {TEST_SUITE_TOKEN}"}

def test_auth_login_endpoint():
    # 1. Unauthenticated client (no headers)
    unauth_client = TestClient(app)
    unauth_resp = unauth_client.get("/api/db/status")
    assert unauth_resp.status_code == 401

    # 2. Invalid credentials
    bad_login = unauth_client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert bad_login.status_code == 401
    assert "Invalid User ID or Password" in bad_login.json()["detail"]

    # 3. Valid credentials for Logistics Operator
    good_login = unauth_client.post("/api/auth/login", json={"username": "admin", "password": "admin123", "role": "logistics_operator"})
    assert good_login.status_code == 200
    token_data = good_login.json()
    assert "access_token" in token_data
    assert token_data["role"] == "logistics_operator"

    # 4. Valid credentials for Delivery Team
    delivery_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    assert delivery_login.status_code == 200
    assert delivery_login.json()["role"] == "delivery_team"

    # 5. Valid credentials for Transport Team
    transport_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    assert transport_login.status_code == 200
    assert transport_login.json()["role"] == "transport_team"

    # 6. Wrong role + valid credentials MUST be rejected
    wrong_role_login = unauth_client.post("/api/auth/login", json={"username": "admin", "password": "admin123", "role": "delivery_team"})
    assert wrong_role_login.status_code == 401
    assert "Invalid User ID or Password" in wrong_role_login.json()["detail"]

    # 7. Access protected route with acquired token
    authed_resp = unauth_client.get("/api/db/status", headers={"Authorization": f"Bearer {token_data['access_token']}"})
    assert authed_resp.status_code == 200

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"

def test_data_summary_endpoint():
    response = client.get("/api/data/summary")
    assert response.status_code == 200
    data = response.json()
    assert "num_nodes" in data
    assert "num_customers" in data

def test_scenarios_endpoint():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) >= 5

def test_predict_disruption_endpoint():
    payload = {
        "disruption_id": "TEST_API_DISR",
        "disruption_type": "severe_congestion",
        "location_node_id": "NODE_FDR_DRIVE",
        "location_name": "FDR Drive Northbound",
        "severity_level": 3.8,
        "wind_speed_mph": 12.0,
        "precipitation_inches": 0.5,
        "visibility_miles": 4.5,
        "temperature_f": 42.0,
        "road_capacity_reduction_pct": 75.0,
        "average_speed_mph": 8.5,
        "normal_speed_mph": 45.0,
        "active_vehicle_incident": True,
        "description": "Multi-vehicle accident on FDR Drive"
    }
    response = client.post("/api/disruption/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data
    assert "confidence" in data
    assert "shap_feature_importance" in data

def test_analyze_disruption_end_to_end_endpoint():
    payload = {
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
    response = client.post("/api/disruption/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "classification" in data
    assert "impact_analysis" in data
    assert "priority_rankings" in data
    assert "recovery_plans" in data
    assert "explainability" in data

    assert "PLAN_A" in data["recovery_plans"]
    assert "PLAN_B" in data["recovery_plans"]
    assert "PLAN_C" in data["recovery_plans"]

def test_analyze_disruption_invalid_location_400():
    payload = {
        "disruption_id": "DISR_INVALID_LOC",
        "disruption_type": "blizzard",
        "location_node_id": "NON_EXISTENT_LOCATION_999",
        "location_name": "Unknown Nowhere Corridor",
        "severity_level": 4.0
    }
    response = client.post("/api/disruption/analyze", json=payload)
    assert response.status_code == 400
    assert "Invalid disruption location" in response.json()["detail"]

def test_accept_and_modify_plan_endpoints():
    # 1. First run analyze
    disr_payload = {
        "disruption_id": "DISR_TEST_ACCEPT",
        "disruption_type": "bridge_closure",
        "location_node_id": "NODE_MANHATTAN_BRIDGE",
        "location_name": "Manhattan Bridge",
        "severity_level": 4.5,
        "road_capacity_reduction_pct": 100.0,
        "average_speed_mph": 0.0,
        "normal_speed_mph": 40.0
    }
    client.post("/api/disruption/analyze", json=disr_payload)

    # 2. Accept Plan B
    accept_payload = {
        "disruption_id": "DISR_TEST_ACCEPT",
        "selected_plan_id": "PLAN_B",
        "operator_id": "OPERATOR_01",
        "operator_notes": "Fast recovery approved to preserve medical SLA."
    }
    resp = client.post("/api/recovery/accept", json=accept_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACCEPTED"
    assert data["applied_plan_id"] == "PLAN_B"

    # 3. Modify Plan A
    modify_payload = {
        "disruption_id": "DISR_TEST_ACCEPT",
        "selected_plan_id": "PLAN_A",
        "operator_id": "OPERATOR_01",
        "operator_notes": "Custom driver break window added.",
        "custom_overrides": {
            "extra_duration_mins": 15.0,
            "notes": "Added 15m driver rest stop"
        }
    }
    resp_mod = client.post("/api/recovery/modify", json=modify_payload)
    assert resp_mod.status_code == 200
    data_mod = resp_mod.json()
    assert data_mod["status"] == "MODIFIED_AND_ACCEPTED"
    assert data_mod["applied_plan_id"] == "PLAN_A"

def test_ml_metrics_endpoint():
    response = client.get("/api/ml/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "accuracy" in data
    assert "macro_f1" in data
    assert "class_wise_metrics" in data
    assert "confusion_matrix" in data

def test_active_incidents_endpoint():
    # 1. Unauthenticated request should be rejected with 401
    unauth_client = TestClient(app)
    unauth_resp = unauth_client.get("/api/incidents/active")
    assert unauth_resp.status_code == 401

    # 2. Authenticated request should return ActiveIncidentResponse schema
    response = client.get("/api/incidents/active")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert "disruption_id" in data
    assert "disruption_input" in data
    assert "llm_team_notification" in data
    assert "llm_provider_info" in data
    assert "impact_analysis" in data

def test_transport_team_portal_backend_rules():
    unauth_client = TestClient(app)
    # 1. Login as transport_team
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    assert t_login.status_code == 200
    t_token = t_login.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # 2. Transport user submits disruption report (POST /api/disruption/report)
    report_payload = {
        "disruption_id": "DISR_TRP_TEST_01",
        "disruption_type": "severe_congestion",
        "location_node_id": "NODE_LINCOLN_TUNNEL",
        "location_name": "Lincoln Tunnel Access",
        "severity_level": 4.2,
        "description": "Transport driver reported heavy congestion"
    }
    rep_resp = unauth_client.post("/api/disruption/report", json=report_payload, headers=t_headers)
    assert rep_resp.status_code == 200
    analysis = rep_resp.json()
    assert "PLAN_A" in analysis["recovery_plans"]
    assert "PLAN_B" in analysis["recovery_plans"]

    # 3. Transport user attempts to accept recovery plan -> MUST BE REJECTED WITH 403 FORBIDDEN
    accept_payload = {
        "disruption_id": "DISR_TRP_TEST_01",
        "selected_plan_id": "PLAN_B"
    }
    forbidden_accept = unauth_client.post("/api/recovery/accept", json=accept_payload, headers=t_headers)
    assert forbidden_accept.status_code == 403
    assert "Role 'transport_team' is not authorized" in forbidden_accept.json()["detail"]

    # 4. Transport user attempts to modify recovery plan -> MUST BE REJECTED WITH 403 FORBIDDEN
    modify_payload = {
        "disruption_id": "DISR_TRP_TEST_01",
        "selected_plan_id": "PLAN_A"
    }
    forbidden_modify = unauth_client.post("/api/recovery/modify", json=modify_payload, headers=t_headers)
    assert forbidden_modify.status_code == 403
    assert "Role 'transport_team' is not authorized" in forbidden_modify.json()["detail"]

def test_delivery_team_portal_backend_rules():
    unauth_client = TestClient(app)
    # 1. Login as delivery_team
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    assert d_login.status_code == 200
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    # 2. Delivery user fetches affected deliveries (GET /api/deliveries/affected)
    affected_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers)
    assert affected_resp.status_code == 200
    data = affected_resp.json()
    assert data["status"] == "ACTIVE"
    assert "affected_deliveries" in data
    assert "priority_rankings" in data
    assert "llm_team_notification" in data

    # Verify data sanitization: operator cost metrics are not in DeliveryPortalResponse schema
    assert "total_cost_usd" not in data
    assert "operator_notes" not in data

    # 3. Delivery user acknowledges delivery (POST /api/deliveries/acknowledge)
    ack_payload = {"delivery_id": "DELIV_001", "acknowledged_by": "delivery"}
    ack_resp = unauth_client.post("/api/deliveries/acknowledge", json=ack_payload, headers=d_headers)
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # 4. Delivery user attempts to submit disruption report -> MUST BE REJECTED WITH 403 FORBIDDEN
    rep_payload = {
        "disruption_id": "DISR_UNAUTH",
        "disruption_type": "blizzard",
        "location_node_id": "NODE_MIDTOWN_HUB",
        "location_name": "Midtown",
        "severity_level": 4.0
    }
    forbidden_rep = unauth_client.post("/api/disruption/report", json=rep_payload, headers=d_headers)
    assert forbidden_rep.status_code == 403
    assert "Role 'delivery_team' is not authorized" in forbidden_rep.json()["detail"]

    # 5. Delivery user attempts to accept recovery plan -> MUST BE REJECTED WITH 403 FORBIDDEN
    forbidden_accept = unauth_client.post("/api/recovery/accept", json={"disruption_id": "D1", "selected_plan_id": "PLAN_A"}, headers=d_headers)
    assert forbidden_accept.status_code == 403
    assert "Role 'delivery_team' is not authorized" in forbidden_accept.json()["detail"]

def test_phase4_reliability_persistence_and_reporter_identity():
    unauth_client = TestClient(app)

    # 1. Login as transport and report disruption
    t_login = unauth_client.post("/api/auth/login", json={"username": "transport", "password": "transport123", "role": "transport_team"})
    t_token = t_login.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    report_payload = {
        "disruption_id": "DISR_PHASE4_001",
        "disruption_type": "flooding",
        "location_node_id": "NODE_QUEENS_TUNNEL",
        "location_name": "Queens Midtown Tunnel",
        "severity_level": 4.5,
        "description": "Flash flood reported by transport driver"
    }
    rep_resp = unauth_client.post("/api/disruption/report", json=report_payload, headers=t_headers)
    assert rep_resp.status_code == 200

    # Verify reporter identity in DB via repository query
    from app.db.repository import DatabaseRepository
    repo = DatabaseRepository()
    db_disr = repo.get_latest_disruptions(limit=1)[0]
    assert db_disr.reported_by == "transport"

    # 2. Login as delivery and record delivery acknowledgement in DB
    d_login = unauth_client.post("/api/auth/login", json={"username": "delivery", "password": "delivery123", "role": "delivery_team"})
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    ack_payload = {"delivery_id": "DELIV_SPECIFIC_101", "acknowledged_by": "delivery"}
    ack_resp = unauth_client.post("/api/deliveries/acknowledge", json=ack_payload, headers=d_headers)
    assert ack_resp.status_code == 200

    # Verify persisted acknowledgement retrieved in subsequent session request
    aff_resp = unauth_client.get("/api/deliveries/affected", headers=d_headers)
    assert aff_resp.status_code == 200
    aff_data = aff_resp.json()
    assert "acknowledged_deliveries" in aff_data
    ack_ids = [item["delivery_id"] for item in aff_data["acknowledged_deliveries"]]
    assert "DELIV_SPECIFIC_101" in ack_ids
    assert "DELIV_UNRELATED_999" not in ack_ids




