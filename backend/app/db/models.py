import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.db.config import Base

# CRS Reference: WGS 84 (EPSG:4326) standard latitude/longitude coordinates
SRID_EPSG = 4326

class DepotModel(Base):
    __tablename__ = "depots"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    node_id = Column(String(50), nullable=False)
    capacity_vehicles = Column(Integer, default=20)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    
    # PostGIS Spatial Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="POINT", srid=SRID_EPSG), nullable=True)

    vehicles = relationship("VehicleModel", back_populates="depot")

class RoadSegmentModel(Base):
    __tablename__ = "road_segments"

    id = Column(String(50), primary_key=True)
    u_node = Column(String(50), nullable=False)
    v_node = Column(String(50), nullable=False)
    distance_miles = Column(Float, nullable=False)
    free_flow_speed_mph = Column(Float, nullable=False)
    capacity_vehicles_per_hr = Column(Float, nullable=False)
    
    # PostGIS LineString Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=SRID_EPSG), nullable=True)

class CustomerModel(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    node_id = Column(String(50), nullable=False)
    demand_kg = Column(Float, nullable=False)
    service_time_mins = Column(Integer, default=15)
    sla_start = Column(String(10), nullable=False)
    sla_end = Column(String(10), nullable=False)
    sla_minutes_from_start = Column(Integer, nullable=False)
    item_value_usd = Column(Float, default=10000.0)
    is_perishable = Column(Boolean, default=False)
    penalty_per_hour_late = Column(Float, default=200.0)
    priority_tier = Column(String(20), default="MEDIUM")
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    # PostGIS Spatial Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="POINT", srid=SRID_EPSG), nullable=True)

    deliveries = relationship("DeliveryModel", back_populates="customer")

class VehicleModel(Base):
    __tablename__ = "vehicles"

    id = Column(String(50), primary_key=True)
    driver_name = Column(String(100), nullable=False)
    capacity_kg = Column(Float, nullable=False)
    depot_id = Column(String(50), ForeignKey("depots.id"), nullable=False)
    home_node = Column(String(50), nullable=False)
    cost_per_mile = Column(Float, default=2.5)
    status = Column(String(30), default="ACTIVE") # ACTIVE, DELAYED, BROKEN_DOWN
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)

    # PostGIS Spatial Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="POINT", srid=SRID_EPSG), nullable=True)

    depot = relationship("DepotModel", back_populates="vehicles")
    routes = relationship("RouteModel", back_populates="vehicle")
    deliveries = relationship("DeliveryModel", back_populates="assigned_vehicle")

class RouteModel(Base):
    __tablename__ = "routes"

    id = Column(String(50), primary_key=True)
    vehicle_id = Column(String(50), ForeignKey("vehicles.id"), nullable=False)
    assigned_segment_ids = Column(Text, nullable=False) # JSON encoded list of segment IDs
    planned_duration_mins = Column(Float, nullable=False)
    planned_distance_miles = Column(Float, nullable=False)
    stops_json = Column(Text, nullable=False) # JSON encoded list of stops

    # PostGIS LineString Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=SRID_EPSG), nullable=True)

    vehicle = relationship("VehicleModel", back_populates="routes")
    deliveries = relationship("DeliveryModel", back_populates="route")

class DeliveryModel(Base):
    __tablename__ = "deliveries"

    id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    route_id = Column(String(50), ForeignKey("routes.id"), nullable=False)
    assigned_vehicle_id = Column(String(50), ForeignKey("vehicles.id"), nullable=False)
    stop_seq = Column(Integer, nullable=False)
    planned_eta = Column(String(10), nullable=False)
    projected_eta = Column(String(10), nullable=True)
    delay_minutes = Column(Float, default=0.0)
    sla_violated = Column(Boolean, default=False)
    priority_score = Column(Float, default=50.0)

    customer = relationship("CustomerModel", back_populates="deliveries")
    route = relationship("RouteModel", back_populates="deliveries")
    assigned_vehicle = relationship("VehicleModel", back_populates="deliveries")

class DisruptionModel(Base):
    __tablename__ = "disruptions"

    id = Column(String(50), primary_key=True)
    disruption_type = Column(String(50), nullable=False)
    location_node_id = Column(String(50), nullable=False)
    location_name = Column(String(150), nullable=False)
    severity_level = Column(Float, nullable=False)
    wind_speed_mph = Column(Float, default=10.0)
    precipitation_inches = Column(Float, default=0.0)
    visibility_miles = Column(Float, default=10.0)
    temperature_f = Column(Float, default=55.0)
    road_capacity_reduction_pct = Column(Float, default=50.0)
    average_speed_mph = Column(Float, default=15.0)
    normal_speed_mph = Column(Float, default=45.0)
    active_vehicle_incident = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    predicted_class = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    reported_by = Column(String(100), nullable=True) # Authenticated reporter identity
    status = Column(String(30), default="REPORTED") # REPORTED, ANALYZED, RECOVERY_PROPOSED, RECOVERY_APPROVED, RESOLVED, DISMISSED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    # PostGIS Spatial Geometry (EPSG:4326)
    geom = Column(Geometry(geometry_type="POINT", srid=SRID_EPSG), nullable=True)

    recovery_plans = relationship("RecoveryPlanModel", back_populates="disruption")

class DependencyRelationshipModel(Base):
    __tablename__ = "dependency_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(30), nullable=False) # SEGMENT, VEHICLE, ROUTE, DELIVERY
    source_id = Column(String(50), nullable=False)
    target_type = Column(String(30), nullable=False) # ROUTE, VEHICLE, DELIVERY, CUSTOMER
    target_id = Column(String(50), nullable=False)
    relationship_type = Column(String(50), nullable=False) # TRAVERSED_BY, OPERATES, CONTAINS_DELIVERY, SEQUENCE_DEPENDENCY

class RecoveryPlanModel(Base):
    __tablename__ = "recovery_plans"

    id = Column(String(100), primary_key=True) # e.g. DISR_01_PLAN_A
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False)
    plan_id = Column(String(20), nullable=False) # PLAN_A, PLAN_B, PLAN_C
    plan_name = Column(String(100), nullable=False)
    strategy_summary = Column(Text, nullable=False)
    total_distance_miles = Column(Float, nullable=False)
    total_duration_minutes = Column(Float, nullable=False)
    total_cost_usd = Column(Float, nullable=False)
    sla_violations_count = Column(Integer, default=0)
    rescheduled_deliveries_count = Column(Integer, default=0)
    rerouted_vehicles_count = Column(Integer, default=0)
    vehicle_routes_json = Column(Text, nullable=False)
    trade_offs_json = Column(Text, nullable=False)
    rule_reasons_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    disruption = relationship("DisruptionModel", back_populates="recovery_plans")

class PlanSelectionModel(Base):
    __tablename__ = "plan_selections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False)
    selected_plan_id = Column(String(100), ForeignKey("recovery_plans.id"), nullable=False)
    status = Column(String(30), nullable=False) # ACCEPTED, MODIFIED_AND_ACCEPTED
    operator_id = Column(String(50), default="OPERATOR_01")
    operator_notes = Column(Text, nullable=True)
    custom_overrides_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DeliveryAcknowledgementModel(Base):
    __tablename__ = "delivery_acknowledgements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(String(50), nullable=False)
    acknowledged_by = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PlanRecommendationModel(Base):
    __tablename__ = "plan_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False)
    recommended_plan_id = Column(String(50), nullable=True)
    policy_used = Column(String(50), nullable=False)
    criteria_weights_json = Column(Text, nullable=False)
    reasons_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_key = Column(String(100), unique=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    disruption_id = Column(String(50), nullable=True)
    plan_id = Column(String(50), nullable=True)
    recipient_role = Column(String(50), default="all")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(100), nullable=False)
    actor_role = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    state_before_json = Column(Text, nullable=True)
    state_after_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))



