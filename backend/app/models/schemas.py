from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DisruptionInput(BaseModel):
    disruption_id: str = Field(default="DISR_001", description="Unique disruption identifier")
    disruption_type: str = Field(..., description="Type of disruption e.g. blizzard, bridge_closure, vehicle_breakdown, severe_congestion")
    location_node_id: str = Field(..., description="Affected network node or segment ID")
    location_name: str = Field(..., description="Human readable location name")
    severity_level: float = Field(..., ge=1.0, le=5.0, description="Severity rating 1-5")
    wind_speed_mph: float = Field(default=10.0, description="Wind speed in MPH")
    precipitation_inches: float = Field(default=0.0, description="Precipitation in inches")
    visibility_miles: float = Field(default=10.0, description="Visibility distance in miles")
    temperature_f: float = Field(default=55.0, description="Temperature in Fahrenheit")
    road_capacity_reduction_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Percentage reduction in road throughput")
    average_speed_mph: float = Field(default=15.0, description="Observed traffic speed")
    normal_speed_mph: float = Field(default=45.0, description="Baseline free-flow speed")
    active_vehicle_incident: bool = Field(default=False, description="Whether a logistics vehicle is breakdown/incident source")
    description: str = Field(default="", description="Operator notes or description")
    reported_by: Optional[str] = Field(default=None, description="Authenticated reporter identity")
    status: Optional[str] = Field(default="REPORTED", description="Incident lifecycle status")

class DisruptionClassification(BaseModel):
    predicted_class: str
    class_code: int
    confidence: float
    class_probabilities: Dict[str, float]
    shap_feature_importance: Dict[str, float]

class AffectedDelivery(BaseModel):
    delivery_id: str
    customer_id: str
    customer_name: str
    route_id: str
    assigned_vehicle_id: str
    original_eta: str
    projected_eta: str
    delay_minutes: float
    sla_window_end: str
    sla_violated: bool
    priority_score: float
    item_value_usd: float
    is_perishable: bool

class AffectedVehicle(BaseModel):
    vehicle_id: str
    driver_name: str
    capacity_kg: float
    current_load_kg: float
    current_location: str
    assigned_route_id: str
    status: str
    estimated_delay_minutes: float

class AffectedRoute(BaseModel):
    route_id: str
    vehicle_id: str
    blocked_segment_id: str
    total_stops: int
    impacted_stops_count: int
    original_duration_minutes: float
    revised_duration_minutes: float
    extra_distance_miles: float

class ImpactAnalysis(BaseModel):
    affected_routes_count: int
    affected_vehicles_count: int
    affected_deliveries_count: int
    total_expected_delay_minutes: float
    at_risk_sla_count: int
    affected_routes: List[AffectedRoute]
    affected_vehicles: List[AffectedVehicle]
    affected_deliveries: List[AffectedDelivery]

class PriorityItem(BaseModel):
    delivery_id: str
    customer_name: str
    priority_score: float
    priority_tier: str # CRITICAL, HIGH, MEDIUM, LOW
    sla_end_time: str
    minutes_until_sla: float
    delay_minutes: float
    item_value_usd: float
    is_perishable: bool
    penalty_usd_per_hour_late: float
    score_breakdown: Dict[str, float]
    reasoning: str

class VehicleRouteDetail(BaseModel):
    vehicle_id: str
    driver_name: str
    stops: List[Dict[str, Any]]
    total_distance_miles: float
    total_duration_minutes: float
    cost_usd: float

class RecoveryPlan(BaseModel):
    plan_id: str # PLAN_A, PLAN_B, PLAN_C
    plan_name: str
    strategy_summary: str
    total_distance_miles: float
    total_distance_km: float = 0.0
    total_duration_minutes: float
    total_cost_usd: float
    sla_violations_count: int
    rescheduled_deliveries_count: int
    rerouted_vehicles_count: int
    vehicle_routes: List[VehicleRouteDetail]
    trade_offs: List[str]
    rule_reasons: List[str]
    objective_type: Optional[str] = None # SHORTEST_DISTANCE | FASTEST_TRAVEL_TIME | SLA_PROTECTED
    route_nodes: Optional[List[str]] = None
    route_edge_ids: Optional[List[str]] = None
    route_coords: Optional[List[List[float]]] = None
    avoids_disrupted_edge: Optional[bool] = True
    optimization_status: Optional[str] = "FEASIBLE" # FEASIBLE | NO_FEASIBLE_ROUTE
    calculation_inputs: Optional[Dict[str, Any]] = None

class ExplainabilityReport(BaseModel):
    ml_prediction_reasoning: List[str]
    shap_top_drivers: List[Dict[str, Any]]
    network_dependency_cascades: List[str]
    impact_summary_reasons: List[str]
    plan_comparisons: Dict[str, str]
    llm_executive_summary: Optional[str] = None
    llm_plan_comparison: Optional[Dict[str, Any]] = None
    llm_team_notification: Optional[str] = None
    llm_provider_info: Optional[str] = None

class ActiveIncidentResponse(BaseModel):
    status: str = "ACTIVE"
    disruption_id: Optional[str] = None
    disruption_input: Optional[DisruptionInput] = None
    classification: Optional[DisruptionClassification] = None
    impact_analysis: Optional[ImpactAnalysis] = None
    applied_plan_id: Optional[str] = None
    applied_plan: Optional[RecoveryPlan] = None
    all_recovery_plans: Optional[Dict[str, RecoveryPlan]] = None
    llm_executive_summary: Optional[str] = None
    llm_team_notification: Optional[str] = None
    llm_provider_info: Optional[str] = "Deterministic LLM Rule Engine"
    extraction_method: Optional[str] = "Deterministic Rule Parser"
    extraction_reasoning: Optional[str] = None
    is_mismatched_from_form: Optional[bool] = False
    operator_notes: Optional[str] = None
    updated_at: Optional[str] = None

class FullAnalysisResponse(BaseModel):
    disruption_input: DisruptionInput
    classification: DisruptionClassification
    impact_analysis: ImpactAnalysis
    priority_rankings: List[PriorityItem]
    recovery_plans: Dict[str, RecoveryPlan]
    explainability: ExplainabilityReport
    extraction_method: Optional[str] = "Deterministic Rule Parser"
    extraction_reasoning: Optional[str] = None
    is_mismatched_from_form: Optional[bool] = False
    timestamp: str

class PlanSelectionRequest(BaseModel):
    disruption_id: str
    selected_plan_id: str # PLAN_A, PLAN_B, PLAN_C
    operator_id: str = Field(default="OPERATOR_01")
    operator_notes: Optional[str] = None
    custom_overrides: Optional[Dict[str, Any]] = None

class PlanSelectionResponse(BaseModel):
    status: str
    message: str
    disruption_id: str
    applied_plan_id: str
    active_plan: RecoveryPlan
    updated_at: str

class MLMetricsResponse(BaseModel):
    model_name: str
    trained_at: str
    num_samples: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    class_wise_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: List[List[int]]
    feature_importances: Dict[str, float]

class DisruptedSegmentGeometry(BaseModel):
    u_node: str
    v_node: str
    location_name: str
    coords: List[List[float]]

class RouteGeometry(BaseModel):
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    strategy_summary: Optional[str] = None
    total_distance_miles: Optional[float] = None
    total_duration_minutes: Optional[float] = None
    total_cost_usd: Optional[float] = None
    coords: List[List[float]] = []

class DeliveryPortalResponse(BaseModel):
    status: str = "ACTIVE"
    disruption_id: Optional[str] = "NONE"
    disruption_type: Optional[str] = "NONE"
    location_name: Optional[str] = "No Active Incident"
    severity_level: Optional[float] = 0.0
    description: Optional[str] = None
    reported_by: Optional[str] = None
    updated_at: Optional[str] = None
    llm_team_notification: Optional[str] = None
    affected_deliveries_count: int = 0
    at_risk_sla_count: int = 0
    total_expected_delay_minutes: float = 0.0
    affected_deliveries: List[AffectedDelivery] = []
    priority_rankings: List[PriorityItem] = []
    acknowledged_deliveries: Optional[List[Dict[str, Any]]] = None
    disrupted_segment: Optional[DisruptedSegmentGeometry] = None
    original_route: Optional[RouteGeometry] = None
    optimized_route: Optional[RouteGeometry] = None
    all_recovery_plans: Optional[Dict[str, RecoveryPlan]] = None
    path_a: Optional[RecoveryPlan] = None
    path_b: Optional[RecoveryPlan] = None
    optimization_status: Optional[str] = "FEASIBLE"
    infeasibility_reason: Optional[str] = None

class DeliveryAcknowledgeRequest(BaseModel):
    delivery_id: str
    acknowledged_by: str = Field(default="delivery")
    notes: Optional[str] = None

class DeliveryAcknowledgeResponse(BaseModel):
    status: str = "ACKNOWLEDGED"
    delivery_id: str
    acknowledged_by: str
    timestamp: str

class PlanComparisonMetrics(BaseModel):
    plan_id: str
    plan_name: str
    strategy_summary: str
    estimated_travel_time_mins: float
    total_route_distance_miles: float
    estimated_operating_cost_usd: Optional[float] = None
    affected_deliveries_count: int
    projected_sla_breaches_count: int
    high_priority_or_perishable_at_risk_count: int
    vehicle_utilization_pct: Optional[float] = None
    vehicles_count: int
    routes_count: int
    route_feasibility_status: str = "FEASIBLE"
    best_for_label: Optional[str] = None
    benefits: List[str] = []
    trade_offs: List[str] = []

class PlanRecommendationRequest(BaseModel):
    disruption_id: str
    policy: str = Field(default="MINIMIZE_COST", description="Policy: MINIMIZE_COST, MINIMIZE_DELAY, or PROTECT_SLA")

class PlanRecommendationResponse(BaseModel):
    recommended_plan_id: Optional[str]
    policy_used: str
    criteria_and_weights: Dict[str, float]
    supporting_metric_values: Dict[str, Any]
    reasons: List[str]
    warnings: List[str]
    timestamp: str

class PlanComparisonResponse(BaseModel):
    disruption_id: str
    policy_used: str
    plans_comparison: Dict[str, PlanComparisonMetrics]
    recommendation: PlanRecommendationResponse
    timestamp: str

# Phase 6 Schemas
class IncidentStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: REPORTED, ANALYZED, RECOVERY_PROPOSED, RECOVERY_APPROVED, RESOLVED, DISMISSED")

class IncidentStatusUpdateResponse(BaseModel):
    disruption_id: str
    previous_status: str
    current_status: str
    updated_by: str

class NotificationItem(BaseModel):
    id: int
    event_key: str
    event_type: str
    title: str
    message: str
    disruption_id: Optional[str] = None
    plan_id: Optional[str] = None
    recipient_role: str = "all"
    is_read: bool = False
    created_at: Optional[str] = None

class NotificationListResponse(BaseModel):
    notifications: List[NotificationItem]
    unread_count: int

class AuditLogItem(BaseModel):
    id: int
    actor_id: str
    actor_role: str
    action_type: str
    entity_type: str
    entity_id: str
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

class AuditLogListResponse(BaseModel):
    logs: List[AuditLogItem]

class DetailedHealthCheckResponse(BaseModel):
    status: str
    api_status: str
    database: Dict[str, Any]
    models_and_engines: Dict[str, str]
    notification_subsystem: str
    timestamp: str


