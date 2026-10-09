import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement

from app.db.config import SessionLocal, engine, Base
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DeliveryModel, DisruptionModel, DependencyRelationshipModel,
    RecoveryPlanModel, PlanSelectionModel, DeliveryAcknowledgementModel,
    PlanRecommendationModel, NotificationModel, AuditLogModel, SRID_EPSG
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

    def save_disruption(self, disruption: DisruptionInput, predicted_class: str = None, confidence: float = None, reported_by: str = None) -> DisruptionModel:
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
                if reported_by:
                    existing.reported_by = reported_by
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
                    confidence=confidence,
                    reported_by=reported_by
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

    def get_latest_disruptions(self, limit: int = 5) -> List[DisruptionModel]:
        db = self.get_db()
        try:
            return db.query(DisruptionModel).order_by(DisruptionModel.created_at.desc()).limit(limit).all()
        finally:
            if self._db is None:
                db.close()

    def get_latest_active_transport_incident(self) -> Optional[DisruptionModel]:
        """
        Retrieves the newest valid, active disruption explicitly reported by a Transport Agent.
        Filters out resolved, dismissed, test_runner, delivery team, and seeded demo incidents.
        """
        db = self.get_db()
        try:
            demo_ids = [
                "DISR_NYC_BLIZZARD_01",
                "DISR_BRIDGE_CLOSURE_02",
                "DISR_TRUCK_BREAKDOWN_03",
                "DISR_FDR_ACCIDENT_04",
                "DISR_TUNNEL_FLOOD_05",
                "DISR_AUDIT_PROP_01"
            ]
            query = db.query(DisruptionModel).filter(
                DisruptionModel.status.in_(["ACTIVE", "REPORTED", "RECOVERY_APPROVED"]),
                DisruptionModel.reported_by.isnot(None),
                ~DisruptionModel.reported_by.in_(["test_runner", "test_user", "delivery", "logistics_operator", "system", "demo", "SEEDED_DEMO"]),
                ~DisruptionModel.id.in_(demo_ids)
            ).order_by(DisruptionModel.created_at.desc())
            return query.first()
        finally:
            if self._db is None:
                db.close()


    def get_latest_plan_selection(self, disruption_id: str) -> Optional[PlanSelectionModel]:
        db = self.get_db()
        try:
            return db.query(PlanSelectionModel).filter_by(disruption_id=disruption_id).order_by(PlanSelectionModel.updated_at.desc()).first()
        finally:
            if self._db is None:
                db.close()

    def record_delivery_acknowledgement(self, delivery_id: str, acknowledged_by: str, notes: str = None) -> Dict[str, Any]:
        db = self.get_db()
        try:
            ack_obj = DeliveryAcknowledgementModel(
                delivery_id=delivery_id,
                acknowledged_by=acknowledged_by,
                notes=notes
            )
            db.add(ack_obj)
            db.commit()
            db.refresh(ack_obj)
            return {
                "id": ack_obj.id,
                "delivery_id": ack_obj.delivery_id,
                "acknowledged_by": ack_obj.acknowledged_by,
                "notes": ack_obj.notes,
                "timestamp": ack_obj.created_at.isoformat() if ack_obj.created_at else datetime.now().isoformat()
            }
        finally:
            if self._db is None:
                db.close()

    def get_delivery_acknowledgements(self) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(DeliveryAcknowledgementModel).order_by(DeliveryAcknowledgementModel.created_at.desc()).all()
            return [
                {
                    "delivery_id": r.delivery_id,
                    "acknowledged_by": r.acknowledged_by,
                    "notes": r.notes,
                    "timestamp": r.created_at.isoformat() if r.created_at else None
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def record_plan_recommendation(
        self,
        disruption_id: str,
        recommended_plan_id: str,
        policy_used: str,
        criteria_and_weights: Dict[str, Any],
        reasons: List[str]
    ) -> Dict[str, Any]:
        db = self.get_db()
        try:
            rec_obj = PlanRecommendationModel(
                disruption_id=disruption_id,
                recommended_plan_id=recommended_plan_id,
                policy_used=policy_used,
                criteria_weights_json=json.dumps(criteria_and_weights),
                reasons_json=json.dumps(reasons)
            )
            db.add(rec_obj)
            db.commit()
            db.refresh(rec_obj)
            return {
                "id": rec_obj.id,
                "disruption_id": rec_obj.disruption_id,
                "recommended_plan_id": rec_obj.recommended_plan_id,
                "policy_used": rec_obj.policy_used,
                "criteria_and_weights": criteria_and_weights,
                "reasons": reasons,
                "timestamp": rec_obj.created_at.isoformat() if rec_obj.created_at else datetime.now().isoformat()
            }
        finally:
            if self._db is None:
                db.close()

    def get_latest_recommendation(self, disruption_id: str) -> Optional[Dict[str, Any]]:
        db = self.get_db()
        try:
            rec = db.query(PlanRecommendationModel).filter_by(disruption_id=disruption_id).order_by(PlanRecommendationModel.created_at.desc()).first()
            if not rec:
                return None
            return {
                "id": rec.id,
                "disruption_id": rec.disruption_id,
                "recommended_plan_id": rec.recommended_plan_id,
                "policy_used": rec.policy_used,
                "criteria_and_weights": json.loads(rec.criteria_weights_json) if rec.criteria_weights_json else {},
                "reasons": json.loads(rec.reasons_json) if rec.reasons_json else [],
                "timestamp": rec.created_at.isoformat() if rec.created_at else None
            }
        finally:
            if self._db is None:
                db.close()

    def update_disruption_status(
        self, disruption_id: str, new_status: str, actor_id: str = "operator", actor_role: str = "logistics_operator"
    ) -> Dict[str, Any]:
        db = self.get_db()
        try:
            disr = db.query(DisruptionModel).filter_by(id=disruption_id).first()
            if not disr:
                raise ValueError(f"Disruption '{disruption_id}' not found.")

            curr_status = disr.status or "REPORTED"
            new_status_upper = new_status.upper()

            valid_transitions = {
                "REPORTED": ["ANALYZED", "RECOVERY_PROPOSED", "RECOVERY_APPROVED", "DISMISSED"],
                "ANALYZED": ["RECOVERY_PROPOSED", "RECOVERY_APPROVED", "DISMISSED"],
                "RECOVERY_PROPOSED": ["RECOVERY_APPROVED", "DISMISSED"],
                "RECOVERY_APPROVED": ["RESOLVED", "DISMISSED"],
                "RESOLVED": [],
                "DISMISSED": []
            }

            allowed = valid_transitions.get(curr_status, [])
            if new_status_upper != curr_status and new_status_upper not in allowed:
                raise ValueError(f"Invalid status transition from '{curr_status}' to '{new_status_upper}'. Permitted next statuses: {allowed}")

            disr.status = new_status_upper
            db.commit()

            self.record_audit_entry(
                actor_id=actor_id,
                actor_role=actor_role,
                action_type="STATUS_CHANGED",
                entity_type="DISRUPTION",
                entity_id=disruption_id,
                state_before={"status": curr_status},
                state_after={"status": new_status_upper}
            )

            event_key = f"STATUS_CHANGE_{disruption_id}_{new_status_upper}"
            self.create_notification(
                event_key=event_key,
                event_type="INCIDENT_STATUS_CHANGED",
                title=f"Incident Status Updated: {new_status_upper}",
                message=f"Disruption {disruption_id} status changed from {curr_status} to {new_status_upper}.",
                disruption_id=disruption_id,
                recipient_role="all"
            )

            return {
                "disruption_id": disruption_id,
                "previous_status": curr_status,
                "current_status": new_status_upper,
                "updated_by": actor_id
            }
        finally:
            if self._db is None:
                db.close()

    def create_notification(
        self,
        event_key: str,
        event_type: str,
        title: str,
        message: str,
        disruption_id: str = None,
        plan_id: str = None,
        recipient_role: str = "all"
    ) -> Dict[str, Any]:
        db = self.get_db()
        try:
            existing = db.query(NotificationModel).filter_by(event_key=event_key).first()
            if existing:
                return {
                    "id": existing.id,
                    "event_key": existing.event_key,
                    "event_type": existing.event_type,
                    "title": existing.title,
                    "message": existing.message,
                    "disruption_id": existing.disruption_id,
                    "plan_id": existing.plan_id,
                    "recipient_role": existing.recipient_role,
                    "is_read": existing.is_read,
                    "created_at": existing.created_at.isoformat() if existing.created_at else datetime.now().isoformat()
                }

            notif = NotificationModel(
                event_key=event_key,
                event_type=event_type,
                title=title,
                message=message,
                disruption_id=disruption_id,
                plan_id=plan_id,
                recipient_role=recipient_role,
                is_read=False
            )
            db.add(notif)
            db.commit()
            db.refresh(notif)

            return {
                "id": notif.id,
                "event_key": notif.event_key,
                "event_type": notif.event_type,
                "title": notif.title,
                "message": notif.message,
                "disruption_id": notif.disruption_id,
                "plan_id": notif.plan_id,
                "recipient_role": notif.recipient_role,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else datetime.now().isoformat()
            }
        finally:
            if self._db is None:
                db.close()

    def get_notifications_for_role(self, role: str = "all") -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            query = db.query(NotificationModel).filter(
                (NotificationModel.recipient_role == "all") | (NotificationModel.recipient_role == role)
            ).order_by(NotificationModel.created_at.desc()).limit(50)
            records = query.all()
            return [
                {
                    "id": r.id,
                    "event_key": r.event_key,
                    "event_type": r.event_type,
                    "title": r.title,
                    "message": r.message,
                    "disruption_id": r.disruption_id,
                    "plan_id": r.plan_id,
                    "recipient_role": r.recipient_role,
                    "is_read": r.is_read,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()

    def mark_notification_as_read(self, notification_id: int) -> bool:
        db = self.get_db()
        try:
            notif = db.query(NotificationModel).filter_by(id=notification_id).first()
            if notif:
                notif.is_read = True
                db.commit()
                return True
            return False
        finally:
            if self._db is None:
                db.close()

    def record_audit_entry(
        self,
        actor_id: str,
        actor_role: str,
        action_type: str,
        entity_type: str,
        entity_id: str,
        state_before: Dict[str, Any] = None,
        state_after: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        db = self.get_db()
        try:
            entry = AuditLogModel(
                actor_id=actor_id,
                actor_role=actor_role,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                state_before_json=json.dumps(state_before) if state_before else None,
                state_after_json=json.dumps(state_after) if state_after else None
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return {
                "id": entry.id,
                "actor_id": entry.actor_id,
                "actor_role": entry.actor_role,
                "action_type": entry.action_type,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "timestamp": entry.created_at.isoformat() if entry.created_at else datetime.now().isoformat()
            }
        finally:
            if self._db is None:
                db.close()

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            records = db.query(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "actor_id": r.actor_id,
                    "actor_role": r.actor_role,
                    "action_type": r.action_type,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "state_before": json.loads(r.state_before_json) if r.state_before_json else None,
                    "state_after": json.loads(r.state_after_json) if r.state_after_json else None,
                    "timestamp": r.created_at.isoformat() if r.created_at else None
                } for r in records
            ]
        finally:
            if self._db is None:
                db.close()


