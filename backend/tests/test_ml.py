import pytest
import os
from app.ml.dataset import generate_disruption_dataset, get_train_val_test_splits
from app.ml.classifier import DisruptionClassifierService
from app.models.schemas import DisruptionInput

def test_dataset_generation():
    df = generate_disruption_dataset(n_samples=500, seed=42)
    assert len(df) == 500
    assert "target" in df.columns
    assert set(df["target"].unique()).issubset({0, 1, 2, 3, 4})

def test_dataset_splits():
    df = generate_disruption_dataset(n_samples=500, seed=42)
    X_tr, X_val, X_te, y_tr, y_val, y_te, scaler = get_train_val_test_splits(df, seed=42)
    assert len(X_tr) == 350
    assert len(X_val) == 75
    assert len(X_te) == 75

def test_classifier_inference():
    service = DisruptionClassifierService()
    test_input = DisruptionInput(
        disruption_id="TEST_01",
        disruption_type="blizzard",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=4.5,
        wind_speed_mph=35.0,
        precipitation_inches=2.5,
        visibility_miles=0.5,
        temperature_f=24.0,
        road_capacity_reduction_pct=80.0,
        average_speed_mph=5.0,
        normal_speed_mph=40.0,
        active_vehicle_incident=False
    )
    result = service.predict(test_input)
    assert result.predicted_class in ["SEVERE_WEATHER", "ROAD_CLOSURE", "SEVERE_CONGESTION"]
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.class_probabilities) == 5
    assert len(result.shap_feature_importance) > 0
