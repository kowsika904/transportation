import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement

from app.db.config import SessionLocal, engine, Base
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DeliveryModel, DisruptionModel, DependencyRelationshipModel,
    RecoveryPlanModel, PlanSelectionModel, SRID_EPSG
)
from app.models.schemas import DisruptionInput, RecoveryPlan

class DatabaseRepository:
    def __init__(self, db: Session = None):
        self._db = db

    def get_db(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    def get_all_depots(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(DepotModel).all()
            return [
                {
                    "depot_id": r.id,
                    "name": r.name,
                    "node_id": r.node_id,
                    "capacity_vehicles": r.capacity_vehicles,
                    "lat": r.lat,
                    "lon": r.lon
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def get_all_road_segments(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(RoadSegmentModel).all()
            return [
                {
                    "id": r.id,
                    "u": r.u_node,
                    "v": r.v_node,
                    "distance_miles": r.distance_miles,
                    "free_flow_speed_mph": r.free_flow_speed_mph,
                    "capacity_vehicles_per_hr": r.capacity_vehicles_per_hr
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def get_all_customers(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(CustomerModel).all()
            return [
                {
                    "customer_id": r.id,
                    "name": r.name,
                    "node_id": r.node_id,
                    "demand_kg": r.demand_kg,
                    "service_time_mins": r.service_time_mins,
                    "sla_start": r.sla_start,
                    "sla_end": r.sla_end,
                    "sla_minutes_from_start": r.sla_minutes_from_start,
                    "item_value_usd": r.item_value_usd,
                    "is_perishable": r.is_perishable,
                    "penalty_per_hour_late": r.penalty_per_hour_late,
                    "priority_tier": r.priority_tier,
                    "lat": r.lat,
                    "lon": r.lon
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def get_all_vehicles(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(VehicleModel).all()
            return [
                {
                    "vehicle_id": r.id,
                    "driver_name": r.driver_name,
                    "capacity_kg": r.capacity_kg,
                    "depot_id": r.depot_id,
                    "home_node": r.home_node,
                    "cost_per_mile": r.cost_per_mile,
                    "status": r.status,
                    "lat": r.current_lat,
                    "lon": r.current_lon
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def get_all_routes(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(RouteModel).all()
            return [
                {
                    "route_id": r.id,
                    "vehicle_id": r.vehicle_id,
                    "stops": json.loads(r.stops_json),
                    "assigned_segment_ids": json.loads(r.assigned_segment_ids),
                    "planned_duration_mins": r.planned_duration_mins,
                    "planned_distance_miles": r.planned_distance_miles
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def save_disruption(self, disruption: DisruptionInput, predicted_class: str = None, confidence: float = None) -> DisruptionModel:
        db = self.get_db()
        try:
            existing = db.query(DisruptionModel).filter_by(id=disruption.disruption_id).first()
            if existing:
                existing.disruption_type = disruption.disruption_type
                existing.location_node_id = disruption.location_node_id
                existing.location_name = disruption.location_name
                existing.severity_level = disruption.severity_level
                existing.wind_speed_mph = disruption.wind_speed_mph
                existing.precipitation_inches = disruption.precipitation_inches
                existing.visibility_miles = disruption.visibility_miles
                existing.temperature_f = disruption.temperature_f
                existing.road_capacity_reduction_pct = disruption.road_capacity_reduction_pct
                existing.average_speed_mph = disruption.average_speed_mph
                existing.normal_speed_mph = disruption.normal_speed_mph
                existing.active_vehicle_incident = disruption.active_vehicle_incident
                existing.description = disruption.description
                if predicted_class:
                    existing.predicted_class = predicted_class
                    existing.confidence = confidence
                db.commit()
                return existing
            else:
                disr_obj = DisruptionModel(
                    id=disruption.disruption_id,
                    disruption_type=disruption.disruption_type,
                    location_node_id=disruption.location_node_id,
                    location_name=disruption.location_name,
                    severity_level=disruption.severity_level,
                    wind_speed_mph=disruption.wind_speed_mph,
                    precipitation_inches=disruption.precipitation_inches,
                    visibility_miles=disruption.visibility_miles,
                    temperature_f=disruption.temperature_f,
                    road_capacity_reduction_pct=disruption.road_capacity_reduction_pct,
                    average_speed_mph=disruption.average_speed_mph,
                    normal_speed_mph=disruption.normal_speed_mph,
                    active_vehicle_incident=disruption.active_vehicle_incident,
                    description=disruption.description,
                    predicted_class=predicted_class,
                    confidence=confidence
                )
                db.add(disr_obj)
                db.commit()
                return disr_obj
        finally:
            if self._db is None:
                db.close()

    def save_recovery_plans(self, disruption_id: str, plans: Dict[str, RecoveryPlan]) -> List[RecoveryPlanModel]:
        db = self.get_db()
        try:
            saved = []
            for p_key, plan in plans.items():
                db_plan_id = f"{disruption_id}_{plan.plan_id}"
                existing = db.query(RecoveryPlanModel).filter_by(id=db_plan_id).first()
                if existing:
                    existing.strategy_summary = plan.strategy_summary
                    existing.total_distance_miles = plan.total_distance_miles
                    existing.total_duration_minutes = plan.total_duration_minutes
                    existing.total_cost_usd = plan.total_cost_usd
                    existing.sla_violations_count = plan.sla_violations_count
                    existing.rescheduled_deliveries_count = plan.rescheduled_deliveries_count
                    existing.rerouted_vehicles_count = plan.rerouted_vehicles_count
                    existing.vehicle_routes_json = json.dumps([vr.model_dump() for vr in plan.vehicle_routes])
                    existing.trade_offs_json = json.dumps(plan.trade_offs)
                    existing.rule_reasons_json = json.dumps(plan.rule_reasons)
                    saved.append(existing)
                else:
                    rec_obj = RecoveryPlanModel(
                        id=db_plan_id,
                        disruption_id=disruption_id,
                        plan_id=plan.plan_id,
                        plan_name=plan.plan_name,
                        strategy_summary=plan.strategy_summary,
                        total_distance_miles=plan.total_distance_miles,
                        total_duration_minutes=plan.total_duration_minutes,
                        total_cost_usd=plan.total_cost_usd,
                        sla_violations_count=plan.sla_violations_count,
                        rescheduled_deliveries_count=plan.rescheduled_deliveries_count,
                        rerouted_vehicles_count=plan.rerouted_vehicles_count,
                        vehicle_routes_json=json.dumps([vr.model_dump() for vr in plan.vehicle_routes]),
                        trade_offs_json=json.dumps(plan.trade_offs),
                        rule_reasons_json=json.dumps(plan.rule_reasons)
                    )
                    db.add(rec_obj)
                    saved.append(rec_obj)
            db.commit()
            return saved
        finally:
            if self._db is None:
                db.close()

    def record_plan_selection(
        self,
        disruption_id: str,
        selected_plan_id: str,
        status: str,
        operator_id: str = "OPERATOR_01",
        operator_notes: str = None,
        custom_overrides: dict = None
    ) -> PlanSelectionModel:
        db = self.get_db()
        try:
            full_plan_key = f"{disruption_id}_{selected_plan_id}" if not selected_plan_id.startswith(disruption_id) else selected_plan_id
            sel_obj = PlanSelectionModel(
                disruption_id=disruption_id,
                selected_plan_id=full_plan_key,
                status=status,
                operator_id=operator_id,
                operator_notes=operator_notes,
                custom_overrides_json=json.dumps(custom_overrides) if custom_overrides else None
            )
            db.add(sel_obj)
            db.commit()
            return sel_obj
        finally:
            if self._db is None:
                db.close()

    def get_recovery_plans_for_disruption(self, disruption_id: str) -> List[RecoveryPlanModel]:
        db = self.get_db()
        try:
            return db.query(RecoveryPlanModel).filter_by(disruption_id=disruption_id).all()
        finally:
            if self._db is None:
                db.close()
