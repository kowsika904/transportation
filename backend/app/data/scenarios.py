from typing import Dict, List, Any
from app.models.schemas import DisruptionInput

REPRODUCIBLE_SCENARIOS: Dict[str, DisruptionInput] = {
    "NYC_BLIZZARD": DisruptionInput(
        disruption_id="DISR_NYC_BLIZZARD_01",
        disruption_type="blizzard",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge & Major NYC Corridors",
        severity_level=4.8,
        wind_speed_mph=42.5,
        precipitation_inches=3.2, # Heavy snowfall
        visibility_miles=0.3, # Near zero visibility
        temperature_f=22.0,
        road_capacity_reduction_pct=85.0,
        average_speed_mph=6.2,
        normal_speed_mph=40.0,
        active_vehicle_incident=False,
        description="Category 4 Severe Winter Blizzard impacting bridges, FDR Drive, and arterial logistics routes across Manhattan and Brooklyn."
    ),
    "MANHATTAN_BRIDGE_CLOSURE": DisruptionInput(
        disruption_id="DISR_BRIDGE_CLOSURE_02",
        disruption_type="bridge_closure",
        location_node_id="NODE_MANHATTAN_BRIDGE",
        location_name="Manhattan Bridge Upper & Lower Decks",
        severity_level=4.5,
        wind_speed_mph=15.0,
        precipitation_inches=0.0,
        visibility_miles=9.0,
        temperature_f=48.0,
        road_capacity_reduction_pct=100.0, # Complete blockage
        average_speed_mph=0.0,
        normal_speed_mph=40.0,
        active_vehicle_incident=False,
        description="Emergency structural inspection forces complete closure of Manhattan Bridge in both directions."
    ),
    "VEHICLE_BREAKDOWN_QUEENS": DisruptionInput(
        disruption_id="DISR_TRUCK_BREAKDOWN_03",
        disruption_type="truck_breakdown",
        location_node_id="NODE_QUEENS_DC",
        location_name="Queens Logistics Hub Exit Ramp",
        severity_level=3.2,
        wind_speed_mph=10.0,
        precipitation_inches=0.1,
        visibility_miles=8.5,
        temperature_f=55.0,
        road_capacity_reduction_pct=60.0,
        average_speed_mph=12.0,
        normal_speed_mph=40.0,
        active_vehicle_incident=True, # Heavy freight vehicle breakdown
        description="Heavy freight delivery truck (VEH_03) engine failure blocking main egress lane out of Queens DC."
    ),
    "FDR_SEVERE_ACCIDENT": DisruptionInput(
        disruption_id="DISR_FDR_ACCIDENT_04",
        disruption_type="severe_congestion",
        location_node_id="NODE_FDR_DRIVE",
        location_name="FDR Drive Northbound at 34th St",
        severity_level=3.8,
        wind_speed_mph=12.0,
        precipitation_inches=0.5, # Slick rain conditions
        visibility_miles=4.5,
        temperature_f=42.0,
        road_capacity_reduction_pct=75.0,
        average_speed_mph=8.5,
        normal_speed_mph=45.0,
        active_vehicle_incident=True,
        description="Multi-vehicle jackknife collision on FDR Drive Northbound creating 4-mile tailback."
    ),
    "QUEENS_TUNNEL_FLOOD": DisruptionInput(
        disruption_id="DISR_TUNNEL_FLOOD_05",
        disruption_type="severe_weather",
        location_node_id="NODE_QUEENS_TUNNEL",
        location_name="Queens-Midtown Tunnel Westbound",
        severity_level=4.2,
        wind_speed_mph=35.0,
        precipitation_inches=2.8, # Flash torrential rain
        visibility_miles=1.2,
        temperature_f=62.0,
        road_capacity_reduction_pct=90.0,
        average_speed_mph=4.0,
        normal_speed_mph=40.0,
        active_vehicle_incident=False,
        description="Torrential rainfall causing flash flooding in Midtown Tunnel entrance portal, closing 2 of 3 lanes."
    )
}

def get_preconfigured_scenarios() -> List[Dict[str, Any]]:
    return [
        {"key": key, "details": item.model_dump()} for key, item in REPRODUCIBLE_SCENARIOS.items()
    ]
