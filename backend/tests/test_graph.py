import pytest
from app.data.loader import DataLoader
from app.graph.dependency_graph import LogisticsDependencyGraph

def test_dependency_graph_construction():
    data = DataLoader()
    graph_service = LogisticsDependencyGraph(data)
    g = graph_service.graph
    
    assert g.number_of_nodes() > 10
    assert g.number_of_edges() > 10

def test_graph_traversal_disruption_impact():
    data = DataLoader()
    graph_service = LogisticsDependencyGraph(data)
    
    trace = graph_service.trace_disruption_impact("SEG_MANHATTAN_BRIDGE")
    assert trace["disruption_source_id"] == "SEG_MANHATTAN_BRIDGE"
    assert "affected_route_ids" in trace
    assert "affected_vehicle_ids" in trace
    assert "affected_delivery_ids" in trace
