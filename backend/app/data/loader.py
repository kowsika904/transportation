import math
import random
from typing import Dict, List, Any

class DataLoader:
    """
    Ingests and exposes structured data representing:
    1. NYC TLC trip records (realistic travel speeds, congestion profiles across NYC zones)
    2. OSMnx road network topology (nodes, edges, free-flow speeds, segment capacities)
    3. NOAA historical weather attributes
    4. CVRPLIB logistics entities (depots, customers, time windows, vehicle capacities)
    Supports persistent database-backed entities via DatabaseRepository.
    """

    def __init__(self, seed: int = 42, use_db: bool = True):
        random.seed(seed)
        self.nodes = self._generate_osm_nodes()
        self.tlc_speed_benchmarks = self._generate_tlc_zone_speeds()
        self.noaa_baseline_weather = self._generate_noaa_baseline()

        if use_db:
            try:
                from app.db.repository import DatabaseRepository
                repo = DatabaseRepository()
                db_depots = repo.get_all_depots()
                db_edges = repo.get_all_road_segments()
                db_cust = repo.get_all_customers()
                db_veh = repo.get_all_vehicles()
                db_routes = repo.get_all_routes()

                if db_depots and db_edges and db_cust and db_veh and db_routes:
                    self.depots = db_depots
                    self.edges = db_edges
                    self.customers = db_cust
                    self.vehicles = db_veh
                    self.routes = db_routes
                    print("DataLoader initialized with DB-backed entities.")
                    return
            except Exception as e:
                print(f"DataLoader DB fallback to local memory structures: {e}")

        self.edges = self._generate_osm_edges()
        self.depots = self._generate_depots()
        self.customers = self._generate_cvrp_customers()
        self.vehicles = self._generate_fleet()
        self.routes = self._generate_initial_routes()

    def _generate_osm_nodes(self) -> Dict[str, Dict[str, Any]]:
        return {
            "NODE_MIDTOWN_HUB": {"id": "NODE_MIDTOWN_HUB", "name": "Midtown Central Depot", "lat": 40.7549, "lon": -73.9840, "zone": "Midtown"},
            "NODE_QUEENS_DC": {"id": "NODE_QUEENS_DC", "name": "Queens Logistics Distribution Center", "lat": 40.7420, "lon": -73.9350, "zone": "Queens"},
            "NODE_FINANCIAL": {"id": "NODE_FINANCIAL", "name": "Wall Street Financial Hub", "lat": 40.7075, "lon": -74.0090, "zone": "Financial District"},
            "NODE_MANHATTAN_BRIDGE": {"id": "NODE_MANHATTAN_BRIDGE", "name": "Manhattan Bridge Corridor", "lat": 40.7090, "lon": -73.9900, "zone": "Chinatown/DUMBO"},
            "NODE_FDR_DRIVE": {"id": "NODE_FDR_DRIVE", "name": "FDR Drive North Segment", "lat": 40.7300, "lon": -73.9740, "zone": "East Side"},
            "NODE_QUEENS_TUNNEL": {"id": "NODE_QUEENS_TUNNEL", "name": "Queens-Midtown Tunnel Plaza", "lat": 40.7445, "lon": -73.9680, "zone": "Murray Hill"},
            "NODE_BROOKLYN_NAVY": {"id": "NODE_BROOKLYN_NAVY", "name": "Brooklyn Navy Yard Depot", "lat": 40.7010, "lon": -73.9740, "zone": "Brooklyn"},
            "NODE_HARLEM_GATEWAY": {"id": "NODE_HARLEM_GATEWAY", "name": "Harlem Freight Terminal", "lat": 40.8100, "lon": -73.9450, "zone": "Harlem"},
            "NODE_LINCOLN_TUNNEL": {"id": "NODE_LINCOLN_TUNNEL", "name": "Lincoln Tunnel Access Node", "lat": 40.7580, "lon": -74.0010, "zone": "Hell's Kitchen"},
            "NODE_JFK_CARGO": {"id": "NODE_JFK_CARGO", "name": "JFK Logistics Terminal", "lat": 40.6413, "lon": -73.7781, "zone": "Queens Airport"},
        }

    def _generate_osm_edges(self) -> List[Dict[str, Any]]:
        # Connect graph nodes with distance, travel time, and free-flow speed
        return [
            {"id": "SEG_MANHATTAN_BRIDGE", "u": "NODE_FINANCIAL", "v": "NODE_BROOKLYN_NAVY", "distance_miles": 2.5, "free_flow_speed_mph": 40.0, "capacity_vehicles_per_hr": 2500},
            {"id": "SEG_FDR_DRIVE_SOUTH", "u": "NODE_FINANCIAL", "v": "NODE_FDR_DRIVE", "distance_miles": 3.1, "free_flow_speed_mph": 45.0, "capacity_vehicles_per_hr": 3200},
            {"id": "SEG_QUEENS_TUNNEL", "u": "NODE_MIDTOWN_HUB", "v": "NODE_QUEENS_DC", "distance_miles": 4.2, "free_flow_speed_mph": 40.0, "capacity_vehicles_per_hr": 2800},
            {"id": "SEG_MIDTOWN_WEST", "u": "NODE_MIDTOWN_HUB", "v": "NODE_LINCOLN_TUNNEL", "distance_miles": 1.2, "free_flow_speed_mph": 25.0, "capacity_vehicles_per_hr": 1800},
            {"id": "SEG_FDR_NORTH", "u": "NODE_FDR_DRIVE", "v": "NODE_HARLEM_GATEWAY", "distance_miles": 5.8, "free_flow_speed_mph": 50.0, "capacity_vehicles_per_hr": 3500},
            {"id": "SEG_QUEENS_EXPRESSWAY", "u": "NODE_QUEENS_DC", "v": "NODE_JFK_CARGO", "distance_miles": 11.5, "free_flow_speed_mph": 55.0, "capacity_vehicles_per_hr": 4000},
            {"id": "SEG_BROOKLYN_QUEENS_EXP", "u": "NODE_BROOKLYN_NAVY", "v": "NODE_QUEENS_DC", "distance_miles": 6.3, "free_flow_speed_mph": 45.0, "capacity_vehicles_per_hr": 3000},
            {"id": "SEG_HARLEM_CROSS", "u": "NODE_LINCOLN_TUNNEL", "v": "NODE_HARLEM_GATEWAY", "distance_miles": 4.5, "free_flow_speed_mph": 30.0, "capacity_vehicles_per_hr": 2000},
        ]

    def _generate_depots(self) -> List[Dict[str, Any]]:
        return [
            {"depot_id": "DEPOT_01", "name": "Midtown Central Hub", "node_id": "NODE_MIDTOWN_HUB", "capacity_vehicles": 20},
            {"depot_id": "DEPOT_02", "name": "Queens Distribution Center", "node_id": "NODE_QUEENS_DC", "capacity_vehicles": 30},
        ]

    def _generate_cvrp_customers(self) -> List[Dict[str, Any]]:
        # CVRPLIB-like instances with strict time windows, demand weights, SLA priorities
        return [
            {
                "customer_id": "CUST_101",
                "name": "Apex Medical Supplies Hub",
                "node_id": "NODE_FINANCIAL",
                "demand_kg": 450,
                "service_time_mins": 15,
                "sla_start": "08:00",
                "sla_end": "10:30",
                "sla_minutes_from_start": 150, # 10:30 is 150 mins after 08:00
                "item_value_usd": 25000.0,
                "is_perishable": True,
                "penalty_per_hour_late": 500.0,
                "priority_tier": "CRITICAL",
            },
            {
                "customer_id": "CUST_102",
                "name": "Wall Street Trading Corp",
                "node_id": "NODE_FINANCIAL",
                "demand_kg": 200,
                "service_time_mins": 10,
                "sla_start": "08:00",
                "sla_end": "11:00",
                "sla_minutes_from_start": 180,
                "item_value_usd": 8000.0,
                "is_perishable": False,
                "penalty_per_hour_late": 150.0,
                "priority_tier": "HIGH",
            },
            {
                "customer_id": "CUST_103",
                "name": "DUMBO Fresh Organic Foods",
                "node_id": "NODE_BROOKLYN_NAVY",
                "demand_kg": 850,
                "service_time_mins": 20,
                "sla_start": "08:00",
                "sla_end": "10:00",
                "sla_minutes_from_start": 120,
                "item_value_usd": 14000.0,
                "is_perishable": True,
                "penalty_per_hour_late": 350.0,
                "priority_tier": "CRITICAL",
            },
            {
                "customer_id": "CUST_104",
                "name": "East Side Electronics Outlets",
                "node_id": "NODE_FDR_DRIVE",
                "demand_kg": 600,
                "service_time_mins": 15,
                "sla_start": "08:00",
                "sla_end": "12:00",
                "sla_minutes_from_start": 240,
                "item_value_usd": 18000.0,
                "is_perishable": False,
                "penalty_per_hour_late": 200.0,
                "priority_tier": "MEDIUM",
            },
            {
                "customer_id": "CUST_105",
                "name": "Harlem Community Hospital Annex",
                "node_id": "NODE_HARLEM_GATEWAY",
                "demand_kg": 300,
                "service_time_mins": 12,
                "sla_start": "08:00",
                "sla_end": "09:45",
                "sla_minutes_from_start": 105,
                "item_value_usd": 32000.0,
                "is_perishable": True,
                "penalty_per_hour_late": 750.0,
                "priority_tier": "CRITICAL",
            },
            {
                "customer_id": "CUST_106",
                "name": "JFK Express Cargo Terminal",
                "node_id": "NODE_JFK_CARGO",
                "demand_kg": 1200,
                "service_time_mins": 25,
                "sla_start": "08:00",
                "sla_end": "13:00",
                "sla_minutes_from_start": 300,
                "item_value_usd": 45000.0,
                "is_perishable": False,
                "penalty_per_hour_late": 400.0,
                "priority_tier": "HIGH",
            },
        ]

    def _generate_fleet(self) -> List[Dict[str, Any]]:
        return [
            {"vehicle_id": "VEH_01", "driver_name": "Marcus Vance", "capacity_kg": 2500, "depot_id": "DEPOT_01", "home_node": "NODE_MIDTOWN_HUB", "cost_per_mile": 2.5, "status": "ACTIVE"},
            {"vehicle_id": "VEH_02", "driver_name": "Elena Rostova", "capacity_kg": 2000, "depot_id": "DEPOT_01", "home_node": "NODE_MIDTOWN_HUB", "cost_per_mile": 2.2, "status": "ACTIVE"},
            {"vehicle_id": "VEH_03", "driver_name": "David Chen", "capacity_kg": 3000, "depot_id": "DEPOT_02", "home_node": "NODE_QUEENS_DC", "cost_per_mile": 2.8, "status": "ACTIVE"},
            {"vehicle_id": "VEH_04", "driver_name": "Sarah Jenkins", "capacity_kg": 2500, "depot_id": "DEPOT_02", "home_node": "NODE_QUEENS_DC", "cost_per_mile": 2.5, "status": "ACTIVE"},
        ]

    def _generate_initial_routes(self) -> List[Dict[str, Any]]:
        return [
            {
                "route_id": "ROUTE_A",
                "vehicle_id": "VEH_01",
                "stops": [
                    {"stop_seq": 1, "type": "DEPOT", "node_id": "NODE_MIDTOWN_HUB", "customer_id": None},
                    {"stop_seq": 2, "type": "DELIVERY", "node_id": "NODE_FINANCIAL", "customer_id": "CUST_101", "delivery_id": "DELIV_101", "planned_eta": "09:15"},
                    {"stop_seq": 3, "type": "DELIVERY", "node_id": "NODE_BROOKLYN_NAVY", "customer_id": "CUST_103", "delivery_id": "DELIV_103", "planned_eta": "09:50"},
                    {"stop_seq": 4, "type": "DEPOT", "node_id": "NODE_MIDTOWN_HUB", "customer_id": None},
                ],
                "assigned_segment_ids": ["SEG_MIDTOWN_WEST", "SEG_MANHATTAN_BRIDGE"],
                "planned_duration_mins": 110.0,
                "planned_distance_miles": 14.2,
            },
            {
                "route_id": "ROUTE_B",
                "vehicle_id": "VEH_02",
                "stops": [
                    {"stop_seq": 1, "type": "DEPOT", "node_id": "NODE_MIDTOWN_HUB", "customer_id": None},
                    {"stop_seq": 2, "type": "DELIVERY", "node_id": "NODE_FDR_DRIVE", "customer_id": "CUST_104", "delivery_id": "DELIV_104", "planned_eta": "09:30"},
                    {"stop_seq": 3, "type": "DELIVERY", "node_id": "NODE_HARLEM_GATEWAY", "customer_id": "CUST_105", "delivery_id": "DELIV_105", "planned_eta": "10:15"},
                    {"stop_seq": 4, "type": "DEPOT", "node_id": "NODE_MIDTOWN_HUB", "customer_id": None},
                ],
                "assigned_segment_ids": ["SEG_FDR_DRIVE_SOUTH", "SEG_FDR_NORTH"],
                "planned_duration_mins": 95.0,
                "planned_distance_miles": 12.8,
            },
            {
                "route_id": "ROUTE_C",
                "vehicle_id": "VEH_03",
                "stops": [
                    {"stop_seq": 1, "type": "DEPOT", "node_id": "NODE_QUEENS_DC", "customer_id": None},
                    {"stop_seq": 2, "type": "DELIVERY", "node_id": "NODE_FINANCIAL", "customer_id": "CUST_102", "delivery_id": "DELIV_102", "planned_eta": "09:40"},
                    {"stop_seq": 3, "type": "DELIVERY", "node_id": "NODE_JFK_CARGO", "customer_id": "CUST_106", "delivery_id": "DELIV_106", "planned_eta": "11:30"},
                    {"stop_seq": 4, "type": "DEPOT", "node_id": "NODE_QUEENS_DC", "customer_id": None},
                ],
                "assigned_segment_ids": ["SEG_QUEENS_TUNNEL", "SEG_QUEENS_EXPRESSWAY"],
                "planned_duration_mins": 140.0,
                "planned_distance_miles": 22.5,
            },
        ]

    def _generate_tlc_zone_speeds(self) -> Dict[str, float]:
        # TLC trip derived average speeds by zone (mph)
        return {
            "Midtown": 9.5,
            "Financial District": 11.2,
            "Chinatown/DUMBO": 12.8,
            "East Side": 14.0,
            "Queens": 22.4,
            "Brooklyn": 18.5,
            "Harlem": 16.2,
        }

    def _generate_noaa_baseline(self) -> Dict[str, float]:
        return {
            "temp_f": 58.0,
            "precip_in": 0.0,
            "wind_mph": 8.5,
            "vis_miles": 10.0,
            "snow_in": 0.0,
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "num_depots": len(self.depots),
            "num_customers": len(self.customers),
            "num_vehicles": len(self.vehicles),
            "num_active_routes": len(self.routes),
            "tlc_benchmark_zones": list(self.tlc_speed_benchmarks.keys()),
            "noaa_baseline": self.noaa_baseline_weather,
        }
