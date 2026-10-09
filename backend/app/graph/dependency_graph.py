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

    def match_road_segment(self, location_identifier: str) -> List[str]:
        """
        Validates and matches a location string, node ID, or corridor name to exact road segment ID(s).
        Raises ValueError if the location cannot be matched to any valid segment or network node.
        """
        if not location_identifier or not isinstance(location_identifier, str):
            raise ValueError("Location identifier must be a non-empty string.")

        loc_clean = location_identifier.strip()
        loc_upper = loc_clean.upper()

        # 1. Exact segment ID match
        if any(s["id"] == loc_clean for s in self.data_loader.edges):
            return [loc_clean]

        # 2. Match node ID or edge endpoint directly
        segs_by_endpoint = [s["id"] for s in self.data_loader.edges if loc_clean in (s["u"], s["v"])]
        if segs_by_endpoint:
            return sorted(list(set(segs_by_endpoint)))

        # 3. Match by core token (e.g., "Manhattan Bridge" or "NODE_MANHATTAN_BRIDGE" -> SEG_MANHATTAN_BRIDGE)
        loc_normalized = loc_upper.replace(" ", "_").replace("-", "_")
        loc_core = (
            loc_normalized.replace("NODE_", "")
            .replace("SEG_", "")
            .replace("_CORRIDOR", "")
            .replace("_PLAZA", "")
            .replace("_HUB", "")
            .replace("_ACCESS", "")
            .replace("_DC", "")
            .replace("_TERMINAL", "")
        )

        matched = set()
        for edge in self.data_loader.edges:
            e_id = edge["id"].upper()
            u_id = edge["u"].upper()
            v_id = edge["v"].upper()

            if loc_core in e_id or e_id in loc_normalized or loc_core in u_id or loc_core in v_id:
                matched.add(edge["id"])

        if matched:
            return sorted(list(matched))

        # 4. Check nodes dictionary
        node_map = getattr(self.data_loader, "nodes", {})
        for n_id, n_data in node_map.items():
            n_name = n_data.get("name", "").upper()
            n_zone = n_data.get("zone", "").upper()

            if loc_core in n_id.upper() or loc_core in n_name or loc_core in n_zone or n_name in loc_upper:
                for edge in self.data_loader.edges:
                    if n_id in (edge["u"], edge["v"]) or loc_core in edge["id"].upper():
                        matched.add(edge["id"])

        if matched:
            return sorted(list(matched))

        raise ValueError(
            f"Invalid disruption location: '{location_identifier}' does not match any valid road segment or network node in the road network."
        )

    def trace_disruption_impact(self, blocked_node_or_segment_id: str) -> Dict[str, Any]:
        """
        Traverses NetworkX graph from disruption source to find all downstream cascading impacts.
        Strictly validates that the disruption source matches valid road network segments.
        """
        matched_segments = self.match_road_segment(blocked_node_or_segment_id)
        
        affected_nodes = set()
        for seg_id in matched_segments:
            affected_nodes.add(seg_id)
            if self.graph.has_node(seg_id):
                descendants = nx.descendants(self.graph, seg_id)
                affected_nodes.update(descendants)

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

        # Check if any vehicle is directly assigned to an affected route
        for r_id in list(affected_routes):
            for u, v, data in self.graph.edges(data=True):
                if v == r_id and self.graph.nodes[u].get("node_type") == "VEHICLE":
                    affected_vehicles.add(u)

        primary_source_id = matched_segments[0]
        return {
            "disruption_source_id": primary_source_id,
            "matched_segment_ids": matched_segments,
            "total_affected_graph_nodes": len(affected_nodes),
            "affected_route_ids": sorted(list(affected_routes)),
            "affected_vehicle_ids": sorted(list(affected_vehicles)),
            "affected_delivery_ids": sorted(list(affected_deliveries)),
            "affected_customer_ids": sorted(list(affected_customers)),
            "cascade_paths": self._get_cascade_paths(primary_source_id)
        }

    def _get_cascade_paths(self, source_id: str) -> List[str]:
        cascade_strings = []
        if not self.graph.has_node(source_id):
            return cascade_strings
            
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

    def get_road_topology_graph(self, exclude_segment_ids: List[str] = None) -> nx.Graph:
        """
        Builds physical road network graph from data_loader edges,
        optionally excluding disrupted road segment IDs without permanently mutating graph state.
        """
        G = nx.Graph()
        exclude = set(exclude_segment_ids or [])

        # Add physical nodes
        node_map = getattr(self.data_loader, "nodes", {})
        for n_id, n_data in node_map.items():
            G.add_node(n_id, **n_data)

        # Add physical edges
        for edge in self.data_loader.edges:
            seg_id = edge["id"]
            if seg_id in exclude:
                continue
            u = edge["u"]
            v = edge["v"]
            dist = edge["distance_miles"]
            speed = edge["free_flow_speed_mph"]
            weight = dist / max(speed, 1.0) * 60.0 # travel duration in minutes
            G.add_edge(u, v, segment_id=seg_id, distance_miles=dist, speed_mph=speed, weight=weight)

        return G

    def find_alternative_paths(
        self, origin_node: str, destination_node: str, exclude_segment_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates two distinct alternative paths (Path A and Path B) avoiding excluded road segments.
        If endpoints are invalid or unresolvable, raises ValueError.
        """
        if not origin_node or not destination_node:
            raise ValueError("Origin and destination nodes must be specified.")

        G = self.get_road_topology_graph(exclude_segment_ids=exclude_segment_ids)

        if not G.has_node(origin_node) or not G.has_node(destination_node):
            raise ValueError(f"Unresolvable routing endpoints: origin='{origin_node}', destination='{destination_node}' not found in road network graph.")

        if not nx.has_path(G, origin_node, destination_node):
            return {
                "status": "NO_PATH_AVAILABLE",
                "valid_paths_count": 0,
                "paths": [],
                "reason": f"No connected road network path exists between {origin_node} and {destination_node} excluding disrupted segments {exclude_segment_ids}."
            }

        # Find shortest path (Path A - Primary Reroute)
        path_a_nodes = nx.shortest_path(G, source=origin_node, target=destination_node, weight="weight")
        
        path_a_dist = 0.0
        path_a_time = 0.0
        path_a_segs = []
        for i in range(len(path_a_nodes) - 1):
            u, v = path_a_nodes[i], path_a_nodes[i+1]
            edge_data = G[u][v]
            path_a_dist += edge_data["distance_miles"]
            path_a_time += edge_data["weight"]
            path_a_segs.append(edge_data["segment_id"])

        # Find distinct Path B (penalizing Path A's edges)
        G_b = G.copy()
        for i in range(len(path_a_nodes) - 1):
            u, v = path_a_nodes[i], path_a_nodes[i+1]
            G_b[u][v]["weight"] *= 3.0

        if nx.has_path(G_b, origin_node, destination_node):
            path_b_nodes = nx.shortest_path(G_b, source=origin_node, target=destination_node, weight="weight")
            if path_b_nodes == path_a_nodes and len(path_a_nodes) > 2:
                mid_u, mid_v = path_a_nodes[0], path_a_nodes[1]
                G_b2 = G.copy()
                G_b2.remove_edge(mid_u, mid_v)
                if nx.has_path(G_b2, origin_node, destination_node):
                    path_b_nodes = nx.shortest_path(G_b2, source=origin_node, target=destination_node, weight="weight")
        else:
            path_b_nodes = path_a_nodes

        path_b_dist = 0.0
        path_b_time = 0.0
        path_b_segs = []
        for i in range(len(path_b_nodes) - 1):
            u, v = path_b_nodes[i], path_b_nodes[i+1]
            edge_data = G[u][v]
            path_b_dist += edge_data["distance_miles"]
            path_b_time += edge_data["weight"]
            path_b_segs.append(edge_data["segment_id"])

        paths = [
            {
                "path_id": "PATH_A",
                "label": "Path A (Primary Reroute)",
                "color": "#10b981", # Emerald green
                "node_sequence": path_a_nodes,
                "segment_ids": path_a_segs,
                "total_distance_miles": round(path_a_dist, 2),
                "total_duration_minutes": round(path_a_time, 1),
            }
        ]

        if path_b_nodes != path_a_nodes:
            paths.append({
                "path_id": "PATH_B",
                "label": "Path B (Alternative Arterial Reroute)",
                "color": "#06b6d4", # Cyan
                "node_sequence": path_b_nodes,
                "segment_ids": path_b_segs,
                "total_distance_miles": round(path_b_dist, 2),
                "total_duration_minutes": round(path_b_time, 1),
            })

        return {
            "status": "SUCCESS",
            "valid_paths_count": len(paths),
            "paths": paths,
            "excluded_segments": exclude_segment_ids or []
        }


