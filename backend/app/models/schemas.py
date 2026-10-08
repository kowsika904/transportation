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
    total_duration_minutes: float
    total_cost_usd: float
    sla_violations_count: int
    rescheduled_deliveries_count: int
    rerouted_vehicles_count: int
    vehicle_routes: List[VehicleRouteDetail]
    trade_offs: List[str]
    rule_reasons: List[str]

class ExplainabilityReport(BaseModel):
    ml_prediction_reasoning: List[str]
    shap_top_drivers: List[Dict[str, Any]]
    network_dependency_cascades: List[str]
    impact_summary_reasons: List[str]
    plan_comparisons: Dict[str, str]

class FullAnalysisResponse(BaseModel):
    disruption_input: DisruptionInput
    classification: DisruptionClassification
    impact_analysis: ImpactAnalysis
    priority_rankings: List[PriorityItem]
    recovery_plans: Dict[str, RecoveryPlan]
    explainability: ExplainabilityReport
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
