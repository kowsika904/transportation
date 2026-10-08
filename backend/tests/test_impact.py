import pytest
from app.data.loader import DataLoader
from app.graph.dependency_graph import LogisticsDependencyGraph
from app.engines.impact_engine import ImpactEngine
from app.models.schemas import DisruptionInput, DisruptionClassification

def test_impact_engine_evaluation():
    loader = DataLoader()
    graph = LogisticsDependencyGraph(loader)
    engine = ImpactEngine(loader, graph)

    disr = DisruptionInput(
        disruption_id="TEST_IMPACT",
        disruption_type="bridge_closure",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge",
        severity_level=4.5,
        road_capacity_reduction_pct=100.0,
        average_speed_mph=0.0,
        normal_speed_mph=40.0
    )

    clf = DisruptionClassification(
        predicted_class="ROAD_CLOSURE",
        class_code=2,
        confidence=0.95,
        class_probabilities={"ROAD_CLOSURE": 0.95},
        shap_feature_importance={"road_capacity_reduction_pct": 0.4}
    )

    impact = engine.evaluate_impact(disr, clf)
    assert impact.affected_routes_count > 0
    assert impact.affected_vehicles_count > 0
    assert impact.affected_deliveries_count > 0
    assert impact.total_expected_delay_minutes > 0.0
