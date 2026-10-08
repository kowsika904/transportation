import networkx as nx
from typing import Dict, List, Any, Set, Tuple
from app.data.loader import DataLoader

class LogisticsDependencyGraph:
    """
    NetworkX dependency graph connecting:
    - Road Network Segments (e.g., SEG_MANHATTAN_BRIDGE)
    - Routes (e.g., ROUTE_A)
    - Fleet Vehicles (e.g., VEH_01)
    - Deliveries & Customers (e.g., DELIV_101 -> CUST_101)
    - Sequence Dependencies (Stop N -> Stop N+1)
    """

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        self.graph.clear()

        # 1. Add Road Segments
        for edge in self.data_loader.edges:
            seg_id = edge["id"]
            self.graph.add_node(
                seg_id,
                node_type="SEGMENT",
                name=seg_id,
                distance_miles=edge["distance_miles"],
                free_flow_speed=edge["free_flow_speed_mph"],
                capacity=edge["capacity_vehicles_per_hr"]
            )

        # 2. Add Fleet Vehicles
        for veh in self.data_loader.vehicles:
            v_id = veh["vehicle_id"]
            self.graph.add_node(
                v_id,
                node_type="VEHICLE",
                name=f"{v_id} ({veh['driver_name']})",
                capacity_kg=veh["capacity_kg"],
                status=veh["status"]
            )

        # 3. Add Customers
        customer_map = {c["customer_id"]: c for c in self.data_loader.customers}
        for cust_id, cust in customer_map.items():
            self.graph.add_node(
                cust_id,
                node_type="CUSTOMER",
                name=cust["name"],
                sla_end=cust["sla_end"],
                priority_tier=cust["priority_tier"],
                is_perishable=cust["is_perishable"]
            )

        # 4. Add Routes and Deliveries
        for route in self.data_loader.routes:
            r_id = route["route_id"]
            v_id = route["vehicle_id"]
            
            self.graph.add_node(
                r_id,
                node_type="ROUTE",
                name=r_id,
                planned_duration=route["planned_duration_mins"]
            )

            # Edge: Vehicle -> Route
            self.graph.add_edge(v_id, r_id, rel_type="OPERATES")
            self.graph.add_edge(r_id, v_id, rel_type="ASSIGNED_VEHICLE")

            # Edges: Segments -> Route
            for seg_id in route["assigned_segment_ids"]:
                if self.graph.has_node(seg_id):
                    self.graph.add_edge(seg_id, r_id, rel_type="TRAVERSED_BY")

            # Deliveries & Sequence Edges
            previous_deliv_id = None
            for stop in route["stops"]:
                if stop["type"] == "DELIVERY":
                    deliv_id = stop["delivery_id"]
                    cust_id = stop["customer_id"]

                    self.graph.add_node(
                        deliv_id,
                        node_type="DELIVERY",
                        name=deliv_id,
                        route_id=r_id,
                        vehicle_id=v_id,
                        planned_eta=stop["planned_eta"],
                        customer_id=cust_id
                    )

                    # Edge: Route -> Delivery
                    self.graph.add_edge(r_id, deliv_id, rel_type="CONTAINS_DELIVERY")
                    
                    # Edge: Delivery -> Customer
                    if self.graph.has_node(cust_id):
                        self.graph.add_edge(deliv_id, cust_id, rel_type="SERVES_CUSTOMER")

                    # Edge: Sequence Dependency (Delivery N -> Delivery N+1)
                    if previous_deliv_id:
                        self.graph.add_edge(previous_deliv_id, deliv_id, rel_type="SEQUENCE_DEPENDENCY")
                    previous_deliv_id = deliv_id

    def trace_disruption_impact(self, blocked_node_or_segment_id: str) -> Dict[str, Any]:
        """
        Traverses NetworkX graph from disruption source to find all downstream cascading impacts.
        """
        if not self.graph.has_node(blocked_node_or_segment_id):
            # Find nearest or associated segment if a node ID was passed
            associated_segs = [s["id"] for s in self.data_loader.edges if blocked_node_or_segment_id in (s["u"], s["v"], s["id"])]
            target_id = associated_segs[0] if associated_segs else "SEG_MANHATTAN_BRIDGE"
        else:
            target_id = blocked_node_or_segment_id

        # Use NetworkX graph traversal to get all reachable nodes downstream
        descendants = nx.descendants(self.graph, target_id)
        affected_nodes = {target_id}.union(descendants)

        affected_routes = set()
        affected_vehicles = set()
        affected_deliveries = set()
        affected_customers = set()

        for node in affected_nodes:
            n_type = self.graph.nodes[node].get("node_type")
            if n_type == "ROUTE":
                affected_routes.add(node)
            elif n_type == "VEHICLE":
                affected_vehicles.add(node)
            elif n_type == "DELIVERY":
                affected_deliveries.add(node)
            elif n_type == "CUSTOMER":
                affected_customers.add(node)

        # Also check if any vehicle is directly assigned to an affected route
        for r_id in list(affected_routes):
            for u, v, data in self.graph.edges(data=True):
                if v == r_id and self.graph.nodes[u].get("node_type") == "VEHICLE":
                    affected_vehicles.add(u)

        return {
            "disruption_source_id": target_id,
            "total_affected_graph_nodes": len(affected_nodes),
            "affected_route_ids": list(affected_routes),
            "affected_vehicle_ids": list(affected_vehicles),
            "affected_delivery_ids": list(affected_deliveries),
            "affected_customer_ids": list(affected_customers),
            "cascade_paths": self._get_cascade_paths(target_id)
        }

    def _get_cascade_paths(self, source_id: str) -> List[str]:
        cascade_strings = []
        for target in self.graph.nodes:
            if target != source_id and nx.has_path(self.graph, source_id, target):
                try:
                    paths = nx.all_shortest_paths(self.graph, source_id, target)
                    for path in list(paths)[:3]: # limit to top 3 paths
                        path_str = " -> ".join([f"{n}({self.graph.nodes[n].get('node_type', 'NODE')})" for n in path])
                        cascade_strings.append(path_str)
                except Exception:
                    pass
        return cascade_strings[:10]
