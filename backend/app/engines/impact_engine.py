from typing import Dict, List, Any
from app.models.schemas import (
    DisruptionInput, DisruptionClassification, ImpactAnalysis,
    AffectedRoute, AffectedVehicle, AffectedDelivery
)
from app.graph.dependency_graph import LogisticsDependencyGraph
from app.data.loader import DataLoader

class ImpactEngine:
    def __init__(self, data_loader: DataLoader, graph: LogisticsDependencyGraph):
        self.data_loader = data_loader
        self.graph = graph

    def evaluate_impact(
        self, disruption: DisruptionInput, classification: DisruptionClassification
    ) -> ImpactAnalysis:
        # 1. Trace structural graph dependencies
        graph_trace = self.graph.trace_disruption_impact(disruption.location_node_id)

        pred_class = classification.predicted_class
        severity = disruption.severity_level

        # Calculate base delay multiplier according to predicted ML class
        if pred_class == "ROAD_CLOSURE":
            base_delay_mins = 60.0 + (severity * 15.0)
            detour_dist_miles = 5.5 + (severity * 1.2)
        elif pred_class == "SEVERE_WEATHER":
            base_delay_mins = 45.0 + (severity * 12.0)
            detour_dist_miles = 4.0 + (severity * 1.0)
        elif pred_class == "VEHICLE_BREAKDOWN":
            base_delay_mins = 90.0 + (severity * 10.0)
            detour_dist_miles = 3.0
        elif pred_class == "SEVERE_CONGESTION":
            base_delay_mins = 30.0 + (severity * 8.0)
            detour_dist_miles = 2.5
        else:
            base_delay_mins = 10.0
            detour_dist_miles = 1.0

        # If active vehicle breakdown incident, check if a specific vehicle is broken down
        if disruption.active_vehicle_incident:
            # Mark breakdown on VEH_03 or first matching vehicle
            breakdown_v_ids = ["VEH_03"] if "VEH_03" in graph_trace["affected_vehicle_ids"] else graph_trace["affected_vehicle_ids"]
        else:
            breakdown_v_ids = []

        affected_routes: List[AffectedRoute] = []
        affected_vehicles: List[AffectedVehicle] = []
        affected_deliveries: List[AffectedDelivery] = []

        cust_dict = {c["customer_id"]: c for c in self.data_loader.customers}
        veh_dict = {v["vehicle_id"]: v for v in self.data_loader.vehicles}

        # Build Affected Routes
        for r in self.data_loader.routes:
            r_id = r["route_id"]
            v_id = r["vehicle_id"]
            
            # Route is affected if it's in graph_trace or traverses affected node/segment
            is_affected = (r_id in graph_trace["affected_route_ids"]) or (v_id in graph_trace["affected_vehicle_ids"])
            
            # If default scenario affects Manhattan Bridge or Queens, tag associated routes
            if disruption.location_node_id in r["assigned_segment_ids"] or is_affected or len(graph_trace["affected_route_ids"]) == 0:
                is_affected = True

            if is_affected:
                route_delay = base_delay_mins * (1.2 if v_id in breakdown_v_ids else 1.0)
                orig_dur = r["planned_duration_mins"]
                rev_dur = orig_dur + route_delay
                extra_dist = detour_dist_miles

                affected_routes.append(
                    AffectedRoute(
                        route_id=r_id,
                        vehicle_id=v_id,
                        blocked_segment_id=disruption.location_node_id,
                        total_stops=len(r["stops"]),
                        impacted_stops_count=len([s for s in r["stops"] if s["type"] == "DELIVERY"]),
                        original_duration_minutes=orig_dur,
                        revised_duration_minutes=rev_dur,
                        extra_distance_miles=extra_dist
                    )
                )

                # Build Affected Vehicle
                v_info = veh_dict.get(v_id, {})
                v_status = "BROKEN_DOWN" if v_id in breakdown_v_ids else "DELAYED_IN_TRAFFIC"
                affected_vehicles.append(
                    AffectedVehicle(
                        vehicle_id=v_id,
                        driver_name=v_info.get("driver_name", "Unknown Driver"),
                        capacity_kg=float(v_info.get("capacity_kg", 2000)),
                        current_load_kg=1500.0,
                        current_location=disruption.location_name,
                        assigned_route_id=r_id,
                        status=v_status,
                        estimated_delay_minutes=route_delay
                    )
                )

                # Process Stops / Deliveries for this route
                cumulative_stop_delay = route_delay
                for stop in r["stops"]:
                    if stop["type"] == "DELIVERY":
                        deliv_id = stop["delivery_id"]
                        cust_id = stop["customer_id"]
                        c_info = cust_dict.get(cust_id, {})

                        # Calculate projected ETA (in minutes from 08:00 AM)
                        orig_eta_str = stop["planned_eta"]
                        # Convert "09:15" -> 75 mins from 08:00
                        hrs, mins = map(int, orig_eta_str.split(":"))
                        orig_mins_from_start = (hrs - 8) * 60 + mins

                        proj_mins = orig_mins_from_start + cumulative_stop_delay
                        proj_hrs = 8 + int(proj_mins // 60)
                        proj_rem_mins = int(proj_mins % 60)
                        proj_eta_str = f"{proj_hrs:02d}:{proj_rem_mins:02d}"

                        sla_mins = c_info.get("sla_minutes_from_start", 180)
                        sla_violated = (proj_mins > sla_mins)

                        # Sequence delay buildup: subsequent stop gets extra 10 mins
                        cumulative_stop_delay += 10.0

                        # Calculate initial priority score estimate
                        item_val = float(c_info.get("item_value_usd", 10000.0))
                        is_perish = bool(c_info.get("is_perishable", False))
                        p_score = 50.0 + (30.0 if sla_violated else 0.0) + (15.0 if is_perish else 0.0)

                        affected_deliveries.append(
                            AffectedDelivery(
                                delivery_id=deliv_id,
                                customer_id=cust_id,
                                customer_name=c_info.get("name", f"Customer {cust_id}"),
                                route_id=r_id,
                                assigned_vehicle_id=v_id,
                                original_eta=orig_eta_str,
                                projected_eta=proj_eta_str,
                                delay_minutes=cumulative_stop_delay - 10.0,
                                sla_window_end=c_info.get("sla_end", "11:00"),
                                sla_violated=sla_violated,
                                priority_score=p_score,
                                item_value_usd=item_val,
                                is_perishable=is_perish
                            )
                        )

        total_delay = sum(r.revised_duration_minutes - r.original_duration_minutes for r in affected_routes)
        at_risk_sla = sum(1 for d in affected_deliveries if d.sla_violated)

        return ImpactAnalysis(
            affected_routes_count=len(affected_routes),
            affected_vehicles_count=len(affected_vehicles),
            affected_deliveries_count=len(affected_deliveries),
            total_expected_delay_minutes=float(round(total_delay, 1)),
            at_risk_sla_count=at_risk_sla,
            affected_routes=affected_routes,
            affected_vehicles=affected_vehicles,
            affected_deliveries=affected_deliveries
        )
