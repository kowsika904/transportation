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
    assert "ROUTE_A" in trace["affected_route_ids"]
    assert "VEH_01" in trace["affected_vehicle_ids"]
    assert "DELIV_101" in trace["affected_delivery_ids"]
    # Route B should not be affected by Manhattan Bridge closure
    assert "ROUTE_B" not in trace["affected_route_ids"]

def test_road_segment_matching():
    data = DataLoader()
    graph_service = LogisticsDependencyGraph(data)

    # Segment ID match
    segs = graph_service.match_road_segment("SEG_MANHATTAN_BRIDGE")
    assert segs == ["SEG_MANHATTAN_BRIDGE"]

    # Node ID match
    segs_node = graph_service.match_road_segment("NODE_MIDTOWN_HUB")
    assert "SEG_QUEENS_TUNNEL" in segs_node or "SEG_MIDTOWN_WEST" in segs_node

    # Fuzzy/Corridor name match
    segs_fuzzy = graph_service.match_road_segment("Manhattan Bridge")
    assert "SEG_MANHATTAN_BRIDGE" in segs_fuzzy

def test_invalid_location_raises_value_error():
    data = DataLoader()
    graph_service = LogisticsDependencyGraph(data)

    with pytest.raises(ValueError, match="Invalid disruption location"):
        graph_service.match_road_segment("NON_EXISTENT_HIGHWAY_9999")

    with pytest.raises(ValueError, match="Invalid disruption location"):
        graph_service.trace_disruption_impact("UNKNOWN_NODE_XYZ")

