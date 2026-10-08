import json
from datetime import datetime
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement

from app.db.config import engine, SessionLocal, Base, USE_POSTGRES
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DeliveryModel, DisruptionModel, DependencyRelationshipModel,
    RecoveryPlanModel, PlanSelectionModel, SRID_EPSG
)
from app.data.loader import DataLoader
from app.data.scenarios import REPRODUCIBLE_SCENARIOS

def seed_database(db: Session = None) -> dict:
    close_session = False
    if db is None:
        # Create all tables on engine
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_session = True

    try:
        # Clear existing table data cleanly
        db.query(PlanSelectionModel).delete()
        db.query(RecoveryPlanModel).delete()
        db.query(DisruptionModel).delete()
        db.query(DependencyRelationshipModel).delete()
        db.query(DeliveryModel).delete()
        db.query(RouteModel).delete()
        db.query(VehicleModel).delete()
        db.query(CustomerModel).delete()
        db.query(RoadSegmentModel).delete()
        db.query(DepotModel).delete()
        db.commit()

        loader = DataLoader()

        # 1. Seed Depots with PostGIS Geometry
        depot_map = {}
        for d in loader.depots:
            node_info = loader.nodes.get(d["node_id"], {"lat": 40.75, "lon": -73.98})
            wkt_pt = f"POINT({node_info['lon']} {node_info['lat']})"
            depot_obj = DepotModel(
                id=d["depot_id"],
                name=d["name"],
                node_id=d["node_id"],
                capacity_vehicles=d["capacity_vehicles"],
                lat=node_info["lat"],
                lon=node_info["lon"],
                geom=WKTElement(wkt_pt, srid=SRID_EPSG)
            )
            db.add(depot_obj)
            depot_map[d["depot_id"]] = depot_obj

        # 2. Seed Road Segments with PostGIS LineString Geometry
        for e in loader.edges:
            u_node = loader.nodes.get(e["u"], {"lat": 40.75, "lon": -73.98})
            v_node = loader.nodes.get(e["v"], {"lat": 40.71, "lon": -73.99})
            line_wkt = f"LINESTRING({u_node['lon']} {u_node['lat']}, {v_node['lon']} {v_node['lat']})"
            
            seg_obj = RoadSegmentModel(
                id=e["id"],
                u_node=e["u"],
                v_node=e["v"],
                distance_miles=e["distance_miles"],
                free_flow_speed_mph=e["free_flow_speed_mph"],
                capacity_vehicles_per_hr=e["capacity_vehicles_per_hr"],
                geom=WKTElement(line_wkt, srid=SRID_EPSG)
            )
            db.add(seg_obj)

        # 3. Seed Customers with PostGIS Geometry
        for c in loader.customers:
            c_node = loader.nodes.get(c["node_id"], {"lat": 40.75, "lon": -73.98})
            wkt_pt = f"POINT({c_node['lon']} {c_node['lat']})"
            cust_obj = CustomerModel(
                id=c["customer_id"],
                name=c["name"],
                node_id=c["node_id"],
                demand_kg=c["demand_kg"],
                service_time_mins=c["service_time_mins"],
                sla_start=c["sla_start"],
                sla_end=c["sla_end"],
                sla_minutes_from_start=c["sla_minutes_from_start"],
                item_value_usd=c["item_value_usd"],
                is_perishable=c["is_perishable"],
                penalty_per_hour_late=c["penalty_per_hour_late"],
                priority_tier=c["priority_tier"],
                lat=c_node["lat"],
                lon=c_node["lon"],
                geom=WKTElement(wkt_pt, srid=SRID_EPSG)
            )
            db.add(cust_obj)

        # 4. Seed Fleet Vehicles with PostGIS Geometry
        for v in loader.vehicles:
            h_node = loader.nodes.get(v["home_node"], {"lat": 40.75, "lon": -73.98})
            wkt_pt = f"POINT({h_node['lon']} {h_node['lat']})"
            veh_obj = VehicleModel(
                id=v["vehicle_id"],
                driver_name=v["driver_name"],
                capacity_kg=v["capacity_kg"],
                depot_id=v["depot_id"],
                home_node=v["home_node"],
                cost_per_mile=v["cost_per_mile"],
                status=v["status"],
                current_lat=h_node["lat"],
                current_lon=h_node["lon"],
                geom=WKTElement(wkt_pt, srid=SRID_EPSG)
            )
            db.add(veh_obj)

        # 5. Seed Initial Routes & Deliveries with PostGIS LineString Geometry
        for r in loader.routes:
            coords = []
            for s in r["stops"]:
                n_info = loader.nodes.get(s["node_id"], {"lat": 40.75, "lon": -73.98})
                coords.append(f"{n_info['lon']} {n_info['lat']}")
            route_line_wkt = f"LINESTRING({', '.join(coords)})" if len(coords) >= 2 else "LINESTRING(-73.98 40.75, -73.99 40.71)"

            route_obj = RouteModel(
                id=r["route_id"],
                vehicle_id=r["vehicle_id"],
                assigned_segment_ids=json.dumps(r["assigned_segment_ids"]),
                planned_duration_mins=r["planned_duration_mins"],
                planned_distance_miles=r["planned_distance_miles"],
                stops_json=json.dumps(r["stops"]),
                geom=WKTElement(route_line_wkt, srid=SRID_EPSG)
            )
            db.add(route_obj)

            # Add Deliveries
            previous_deliv_id = None
            for stop in r["stops"]:
                if stop["type"] == "DELIVERY":
                    deliv_obj = DeliveryModel(
                        id=stop["delivery_id"],
                        customer_id=stop["customer_id"],
                        route_id=r["route_id"],
                        assigned_vehicle_id=r["vehicle_id"],
                        stop_seq=stop["stop_seq"],
                        planned_eta=stop["planned_eta"],
                        projected_eta=stop["planned_eta"],
                        delay_minutes=0.0,
                        sla_violated=False,
                        priority_score=50.0
                    )
                    db.add(deliv_obj)

                    # Add Dependency Relationships
                    db.add(DependencyRelationshipModel(
                        source_type="ROUTE",
                        source_id=r["route_id"],
                        target_type="DELIVERY",
                        target_id=stop["delivery_id"],
                        relationship_type="CONTAINS_DELIVERY"
                    ))
                    db.add(DependencyRelationshipModel(
                        source_type="DELIVERY",
                        source_id=stop["delivery_id"],
                        target_type="CUSTOMER",
                        target_id=stop["customer_id"],
                        relationship_type="SERVES_CUSTOMER"
                    ))
                    if previous_deliv_id:
                        db.add(DependencyRelationshipModel(
                            source_type="DELIVERY",
                            source_id=previous_deliv_id,
                            target_type="DELIVERY",
                            target_id=stop["delivery_id"],
                            relationship_type="SEQUENCE_DEPENDENCY"
                        ))
                    previous_deliv_id = stop["delivery_id"]

            # Vehicle operates Route dependency
            db.add(DependencyRelationshipModel(
                source_type="VEHICLE",
                source_id=r["vehicle_id"],
                target_type="ROUTE",
                target_id=r["route_id"],
                relationship_type="OPERATES"
            ))

            # Segment traversed by Route dependencies
            for seg_id in r["assigned_segment_ids"]:
                db.add(DependencyRelationshipModel(
                    source_type="SEGMENT",
                    source_id=seg_id,
                    target_type="ROUTE",
                    target_id=r["route_id"],
                    relationship_type="TRAVERSED_BY"
                ))

        # 6. Seed Reproducible Disruption Scenarios into DB with PostGIS Geometry
        for key, disr_inp in REPRODUCIBLE_SCENARIOS.items():
            loc_node = loader.nodes.get(disr_inp.location_node_id, {"lat": 40.7090, "lon": -73.9900})
            wkt_pt = f"POINT({loc_node['lon']} {loc_node['lat']})"
            disr_obj = DisruptionModel(
                id=disr_inp.disruption_id,
                disruption_type=disr_inp.disruption_type,
                location_node_id=disr_inp.location_node_id,
                location_name=disr_inp.location_name,
                severity_level=disr_inp.severity_level,
                wind_speed_mph=disr_inp.wind_speed_mph,
                precipitation_inches=disr_inp.precipitation_inches,
                visibility_miles=disr_inp.visibility_miles,
                temperature_f=disr_inp.temperature_f,
                road_capacity_reduction_pct=disr_inp.road_capacity_reduction_pct,
                average_speed_mph=disr_inp.average_speed_mph,
                normal_speed_mph=disr_inp.normal_speed_mph,
                active_vehicle_incident=disr_inp.active_vehicle_incident,
                description=disr_inp.description,
                predicted_class=None,
                confidence=None,
                lat=loc_node["lat"],
                lon=loc_node["lon"],
                geom=WKTElement(wkt_pt, srid=SRID_EPSG)
            )
            db.add(disr_obj)

        db.commit()

        summary = {
            "depots_seeded": len(loader.depots),
            "segments_seeded": len(loader.edges),
            "customers_seeded": len(loader.customers),
            "vehicles_seeded": len(loader.vehicles),
            "routes_seeded": len(loader.routes),
            "disruptions_seeded": len(REPRODUCIBLE_SCENARIOS),
            "database_backend": "PostgreSQL + PostGIS" if USE_POSTGRES else "SQLite (PostGIS geometry formatted)"
        }
        print(f"Database seeded successfully: {summary}")
        return summary
    finally:
        if close_session:
            db.close()

if __name__ == "__main__":
    seed_database()
