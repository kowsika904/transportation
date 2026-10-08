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
    assert "Invalid username or password" in bad_login.json()["detail"]

    # 3. Valid credentials
    good_login = unauth_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert good_login.status_code == 200
    token_data = good_login.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 4. Access protected route with acquired token
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
