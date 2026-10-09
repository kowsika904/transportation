import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.schemas import (
    DisruptionInput, DisruptionClassification, FullAnalysisResponse,
    PlanSelectionRequest, PlanSelectionResponse, MLMetricsResponse,
    ActiveIncidentResponse, DeliveryPortalResponse, DeliveryAcknowledgeRequest,
    DeliveryAcknowledgeResponse, PlanRecommendationRequest, PlanRecommendationResponse,
    PlanComparisonResponse, IncidentStatusUpdateRequest, IncidentStatusUpdateResponse,
    NotificationItem, NotificationListResponse, AuditLogItem, AuditLogListResponse,
    DetailedHealthCheckResponse
)
from app.data.loader import DataLoader
from app.data.scenarios import REPRODUCIBLE_SCENARIOS, get_preconfigured_scenarios
from app.ml.classifier import DisruptionClassifierService
from app.ml.evaluator import get_saved_metrics
from app.graph.dependency_graph import LogisticsDependencyGraph
from app.engines.impact_engine import ImpactEngine
from app.engines.priority_engine import PriorityEngine
from app.engines.recovery_engine import ORToolsRecoveryEngine
from app.engines.explainability_engine import ExplainabilityEngine
from app.engines.decision_support_engine import DecisionSupportEngine
from app.engines.extraction_engine import IncidentExtractor

from app.db.config import engine, USE_POSTGRES, get_db
from app.db.repository import DatabaseRepository
from app.db.seed import seed_database
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DisruptionModel, RecoveryPlanModel, PlanSelectionModel
)

from app.api.auth import verify_token, require_role, get_current_token_info, get_token_info_flexible

router = APIRouter(prefix="/api")

# Singleton DB Repo
repo = DatabaseRepository()

# In-memory singletons for Phase 1 backend engine (initialized with DB-backed DataLoader)
data_loader = DataLoader(use_db=True)
classifier_service = DisruptionClassifierService()
dependency_graph = LogisticsDependencyGraph(data_loader)
impact_engine = ImpactEngine(data_loader, dependency_graph)
priority_engine = PriorityEngine(data_loader)
recovery_engine = ORToolsRecoveryEngine(data_loader, graph=dependency_graph)
explainability_engine = ExplainabilityEngine()
decision_engine = DecisionSupportEngine()
incident_extractor = IncidentExtractor()

# State store for operator plan selections
active_plan_store: Dict[str, Dict[str, Any]] = {}

from sqlalchemy import text

@router.get("/health", response_model=DetailedHealthCheckResponse)
def health_check(db: Session = Depends(get_db)):
    db_connected = False
    db_backend = "PostgreSQL + PostGIS" if USE_POSTGRES else "SQLite (Spatial PostGIS compatibility mode)"
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    engines_readiness = {
        "classifier_service": "READY" if classifier_service else "UNAVAILABLE",
        "dependency_graph": "READY" if dependency_graph else "UNAVAILABLE",
        "impact_engine": "READY" if impact_engine else "UNAVAILABLE",
        "priority_engine": "READY" if priority_engine else "UNAVAILABLE",
        "recovery_engine": "READY" if recovery_engine else "UNAVAILABLE",
        "decision_engine": "READY" if decision_engine else "UNAVAILABLE"
    }

    all_engines_ok = all(v == "READY" for v in engines_readiness.values())
    overall_status = "HEALTHY" if (db_connected and all_engines_ok) else "DEGRADED"

    return DetailedHealthCheckResponse(
        status=overall_status,
        api_status="ONLINE",
        database={
            "status": "CONNECTED" if db_connected else "DISCONNECTED",
            "backend": db_backend
        },
        models_and_engines=engines_readiness,
        notification_subsystem="ONLINE",
        timestamp=datetime.now().isoformat()
    )


@router.get("/db/status")
def get_db_status(db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    try:
        return {
            "status": "CONNECTED",
            "backend": "PostgreSQL + PostGIS" if USE_POSTGRES else "SQLite (PostGIS geometry formatted)",
            "depots_count": db.query(DepotModel).count(),
            "road_segments_count": db.query(RoadSegmentModel).count(),
            "customers_count": db.query(CustomerModel).count(),
            "vehicles_count": db.query(VehicleModel).count(),
            "routes_count": db.query(RouteModel).count(),
            "disruptions_count": db.query(DisruptionModel).count(),
            "recovery_plans_count": db.query(RecoveryPlanModel).count(),
            "plan_selections_count": db.query(PlanSelectionModel).count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database status error: {str(e)}")

@router.post("/db/seed")
def seed_db_endpoint(db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    try:
        summary = seed_database(db)
        return {"status": "SUCCESS", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seed error: {str(e)}")

@router.get("/data/summary")
def get_data_summary(current_user: str = Depends(verify_token)):
    return data_loader.get_summary()

@router.get("/scenarios")
def get_scenarios(current_user: str = Depends(verify_token)):
    return {
        "scenarios": get_preconfigured_scenarios()
    }

@router.post("/disruption/predict", response_model=DisruptionClassification)
def predict_disruption(disruption: DisruptionInput, current_user: str = Depends(verify_token)):
    try:
        return classifier_service.predict(disruption)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Prediction Error: {str(e)}")

@router.post("/disruption/analyze", response_model=FullAnalysisResponse)
def analyze_disruption(disruption: DisruptionInput, current_user: str = Depends(verify_token)):
    """
    Executes core workflow and persists Disruption + Recovery Plans in Database.
    """
    try:
        # 1. Incident Extraction & Structured Field Understanding
        extracted = incident_extractor.extract_from_incident_input(
            description_text=disruption.description,
            form_node_id=disruption.location_node_id,
            form_disruption_type=disruption.disruption_type,
            form_severity=disruption.severity_level,
            form_location_name=disruption.location_name
        )

        # Check location mismatch between submitted message and form location
        if extracted.is_mismatched_from_form:
            raise ValueError(
                f"LOCATION MISMATCH: The submitted incident message specifies corridor '{extracted.location_name}' ({extracted.location_node_id}) "
                f"whereas the form dropdown selected '{disruption.location_name}' ({disruption.location_node_id}). "
                f"Please align the location dropdown with the reported message before submitting."
            )

        # Update disruption input with extracted facts/corridors
        disruption.location_node_id = extracted.location_node_id
        disruption.location_name = extracted.location_name
        disruption.disruption_type = extracted.incident_type
        disruption.severity_level = extracted.severity_level
        if extracted.incident_type == "vehicle_breakdown":
            disruption.active_vehicle_incident = True

        # 2. XGBoost Classification
        classification = classifier_service.predict(disruption)

        # Persist Disruption record in DB with authenticated reporter identity
        if not disruption.reported_by:
            disruption.reported_by = current_user
        repo.save_disruption(disruption, classification.predicted_class, classification.confidence, reported_by=current_user)

        # 3. Impact Engine (using NetworkX dependency graph traversal)
        impact = impact_engine.evaluate_impact(disruption, classification)

        # 4. Priority Engine (Dynamic 0-100 SLA scoring)
        priorities = priority_engine.rank_affected_deliveries(impact.affected_deliveries)

        # 5. OR-Tools Recovery Engine (Plan A: Shortest Distance, Plan B: Fastest Time)
        recovery_plans = recovery_engine.generate_recovery_plans(disruption, priorities)

        # Persist Recovery Plans in DB
        repo.save_recovery_plans(disruption.disruption_id, recovery_plans)

        # 6. Explainability Engine (SHAP + Rule-based reasons)
        explanation = explainability_engine.generate_report(disruption, classification, impact, recovery_plans)

        response = FullAnalysisResponse(
            disruption_input=disruption,
            classification=classification,
            impact_analysis=impact,
            priority_rankings=priorities,
            recovery_plans=recovery_plans,
            explainability=explanation,
            extraction_method=extracted.extraction_method,
            extraction_reasoning=extracted.extraction_reasoning,
            is_mismatched_from_form=extracted.is_mismatched_from_form,
            timestamp=datetime.now().isoformat()
        )

        active_plan_store[disruption.disruption_id] = {
            "analysis": response,
            "selected_plan": None
        }

        # Audit & Notification integration
        repo.record_audit_entry(
            actor_id=current_user,
            actor_role="transport_team" if "transport" in current_user.lower() else "logistics_operator",
            action_type="INCIDENT_CREATED",
            entity_type="DISRUPTION",
            entity_id=disruption.disruption_id,
            state_after={
                "type": disruption.disruption_type,
                "severity": disruption.severity_level,
                "location": disruption.location_name,
                "extraction_method": extracted.extraction_method,
                "is_mismatched": extracted.is_mismatched_from_form
            }
        )
        repo.record_audit_entry(
            actor_id=current_user,
            actor_role="system",
            action_type="PLANS_GENERATED",
            entity_type="RECOVERY_PLAN",
            entity_id=disruption.disruption_id,
            state_after={"plans": list(recovery_plans.keys())}
        )
        repo.create_notification(
            event_key=f"NEW_DISRUPTION_{disruption.disruption_id}",
            event_type="DISRUPTION_REPORTED",
            title=f"New Disruption: {disruption.location_name}",
            message=f"{disruption.disruption_type.replace('_', ' ').title()} (Severity {disruption.severity_level}) reported by {current_user}.",
            disruption_id=disruption.disruption_id,
            recipient_role="all"
        )

        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"End-to-end analysis failure: {str(e)}")

@router.post("/disruption/report", response_model=FullAnalysisResponse)
def report_disruption_endpoint(disruption: DisruptionInput, current_user: str = Depends(require_role(["transport_team"]))):
    """
    Endpoint for Transport Team to report a road disruption.
    Includes de-duplication check, persists disruption & recovery plans in DB, and triggers workflow.
    """
    # De-duplication check: if last active disruption in memory has identical location & type within recent seconds
    if active_plan_store:
        last_id = list(active_plan_store.keys())[-1]
        last_analysis = active_plan_store[last_id]["analysis"]
        last_disr = last_analysis.disruption_input
        if (
            last_disr.location_node_id == disruption.location_node_id
            and last_disr.disruption_type == disruption.disruption_type
            and abs(last_disr.severity_level - disruption.severity_level) < 0.1
            and last_disr.description == disruption.description
        ):
            return last_analysis

    return analyze_disruption(disruption, current_user=current_user)

@router.post("/recovery/accept", response_model=PlanSelectionResponse)
def accept_recovery_plan(request: PlanSelectionRequest, current_user: str = Depends(require_role(["logistics_operator"]))):
    disruption_id = request.disruption_id
    if disruption_id not in active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc and active_db_inc.id == disruption_id:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=current_user)
        else:
            raise HTTPException(status_code=400, detail=f"Disruption '{disruption_id}' not found. Transport Agent must submit an incident report first.")

    store_item = active_plan_store[disruption_id]
    analysis: FullAnalysisResponse = store_item["analysis"]

    selected_id = request.selected_plan_id
    if selected_id not in analysis.recovery_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan ID: {selected_id}. Must be PLAN_A, PLAN_B, or PLAN_C.")

    selected_plan = analysis.recovery_plans[selected_id]
    store_item["selected_plan"] = selected_plan.model_dump()
    store_item["operator_notes"] = request.operator_notes

    # Persist operator selection in Database
    repo.record_plan_selection(
        disruption_id=disruption_id,
        selected_plan_id=selected_id,
        status="ACCEPTED",
        operator_id=request.operator_id,
        operator_notes=request.operator_notes
    )

    # Update Disruption status to RECOVERY_APPROVED
    repo.update_disruption_status(
        disruption_id=disruption_id,
        new_status="RECOVERY_APPROVED",
        actor_id=current_user,
        actor_role="logistics_operator"
    )

    repo.record_audit_entry(
        actor_id=current_user,
        actor_role="logistics_operator",
        action_type="PLAN_ACCEPTED",
        entity_type="RECOVERY_PLAN",
        entity_id=selected_id,
        state_after={"plan_id": selected_id, "notes": request.operator_notes}
    )

    repo.create_notification(
        event_key=f"PLAN_ACCEPTED_{disruption_id}_{selected_id}",
        event_type="RECOVERY_PLAN_ACCEPTED",
        title=f"Recovery Plan Approved: {selected_plan.plan_name}",
        message=f"Operator {current_user} approved recovery plan for disruption {disruption_id}.",
        disruption_id=disruption_id,
        plan_id=selected_id,
        recipient_role="all"
    )

    return PlanSelectionResponse(
        status="ACCEPTED",
        message=f"Operator approved plan '{selected_plan.plan_name}'. Route updates dispatched to fleet.",
        disruption_id=disruption_id,
        applied_plan_id=selected_id,
        active_plan=selected_plan,
        updated_at=datetime.now().isoformat()
    )

@router.post("/recovery/modify", response_model=PlanSelectionResponse)
def modify_recovery_plan(request: PlanSelectionRequest, current_user: str = Depends(require_role(["logistics_operator"]))):

    disruption_id = request.disruption_id
    if disruption_id not in active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc and active_db_inc.id == disruption_id:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=current_user)
        else:
            raise HTTPException(status_code=400, detail=f"Disruption '{disruption_id}' not found. Transport Agent must submit an incident report first.")

    store_item = active_plan_store[disruption_id]
    analysis: FullAnalysisResponse = store_item["analysis"]

    selected_id = request.selected_plan_id
    if selected_id not in analysis.recovery_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan ID: {selected_id}")

    base_plan = analysis.recovery_plans[selected_id].model_copy(deep=True)
    base_plan.plan_name += " (Operator Modified)"
    
    if request.custom_overrides:
        if "extra_duration_mins" in request.custom_overrides:
            base_plan.total_duration_minutes += float(request.custom_overrides["extra_duration_mins"])
        if "notes" in request.custom_overrides:
            base_plan.trade_offs.append(f"Operator override: {request.custom_overrides['notes']}")

    store_item["selected_plan"] = base_plan.model_dump()
    store_item["operator_notes"] = request.operator_notes

    # Persist modified operator selection in Database
    repo.record_plan_selection(
        disruption_id=disruption_id,
        selected_plan_id=selected_id,
        status="MODIFIED_AND_ACCEPTED",
        operator_id=request.operator_id,
        operator_notes=request.operator_notes,
        custom_overrides=request.custom_overrides
    )

    repo.update_disruption_status(
        disruption_id=disruption_id,
        new_status="RECOVERY_APPROVED",
        actor_id=current_user,
        actor_role="logistics_operator"
    )

    repo.record_audit_entry(
        actor_id=current_user,
        actor_role="logistics_operator",
        action_type="PLAN_MODIFIED",
        entity_type="RECOVERY_PLAN",
        entity_id=selected_id,
        state_after={"plan_id": selected_id, "overrides": request.custom_overrides}
    )

    repo.create_notification(
        event_key=f"PLAN_MODIFIED_{disruption_id}_{selected_id}",
        event_type="RECOVERY_PLAN_MODIFIED",
        title=f"Recovery Plan Modified & Approved",
        message=f"Operator {current_user} customized and approved plan for disruption {disruption_id}.",
        disruption_id=disruption_id,
        plan_id=selected_id,
        recipient_role="all"
    )

    return PlanSelectionResponse(
        status="MODIFIED_AND_ACCEPTED",
        message=f"Operator customized and approved plan '{base_plan.plan_name}'. Custom parameters applied.",
        disruption_id=disruption_id,
        applied_plan_id=selected_id,
        active_plan=base_plan,
        updated_at=datetime.now().isoformat()
    )


@router.get("/ml/metrics", response_model=MLMetricsResponse)
def get_ml_metrics(current_user: str = Depends(verify_token)):
    metrics = get_saved_metrics()
    return MLMetricsResponse(
        model_name=metrics["model_name"],
        trained_at=datetime.now().strftime("%Y-%m-%d"),
        num_samples=metrics["num_samples"],
        accuracy=metrics["accuracy"],
        macro_precision=metrics["macro_precision"],
        macro_recall=metrics["macro_recall"],
        macro_f1=metrics["macro_f1"],
        class_wise_metrics=metrics["class_wise_metrics"],
        confusion_matrix=metrics["confusion_matrix"],
        feature_importances=metrics["feature_importances"]
    )

@router.get("/incidents/active", response_model=ActiveIncidentResponse)
def get_active_incident(current_user: str = Depends(verify_token)):
    """
    Shared active incident feed endpoint across Logistics Operator, Transport Team, and Delivery Management.
    Enforces authentication and returns current active disruption submitted by Transport Agent.
    If no disruption has been reported yet, returns NO_ACTIVE_INCIDENT status without inventing fake data.
    """
    if not active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                wind_speed_mph=active_db_inc.wind_speed_mph,
                precipitation_inches=active_db_inc.precipitation_inches,
                visibility_miles=active_db_inc.visibility_miles,
                temperature_f=active_db_inc.temperature_f,
                road_capacity_reduction_pct=active_db_inc.road_capacity_reduction_pct,
                average_speed_mph=active_db_inc.average_speed_mph,
                normal_speed_mph=active_db_inc.normal_speed_mph,
                active_vehicle_incident=active_db_inc.active_vehicle_incident,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=active_db_inc.reported_by or current_user)

    if not active_plan_store:
        return ActiveIncidentResponse(
            status="NO_ACTIVE_INCIDENT",
            disruption_id=None,
            disruption_input=None,
            llm_executive_summary=None,
            llm_team_notification="No incident has been reported by the Transport Team.",
            llm_provider_info="Deterministic LLM Rule Engine",
            updated_at=datetime.now().isoformat()
        )

    disruption_id = list(active_plan_store.keys())[-1]
    store_item = active_plan_store[disruption_id]
    analysis: FullAnalysisResponse = store_item["analysis"]

    applied_plan_obj = None
    applied_plan_id = None

    if store_item.get("selected_plan"):
        selected_dict = store_item["selected_plan"]
        applied_plan_id = selected_dict.get("plan_id")
        applied_plan_obj = selected_dict
    else:
        db_sel = repo.get_latest_plan_selection(disruption_id)
        if db_sel and db_sel.selected_plan_id:
            parts = db_sel.selected_plan_id.split("_")
            raw_id = "_".join(parts[2:]) if len(parts) >= 3 else parts[-1]
            for key, plan in analysis.recovery_plans.items():
                if key == raw_id or plan.plan_id == raw_id:
                    applied_plan_id = plan.plan_id
                    applied_plan_obj = plan.model_dump()
                    break

    llm_summary = analysis.explainability.llm_executive_summary
    llm_notification = analysis.explainability.llm_team_notification
    llm_provider = analysis.explainability.llm_provider_info or "Deterministic LLM Rule Engine (LLM_API_KEY not set)"

    return ActiveIncidentResponse(
        status="ACTIVE",
        disruption_id=disruption_id,
        disruption_input=analysis.disruption_input,
        classification=analysis.classification,
        impact_analysis=analysis.impact_analysis,
        applied_plan_id=applied_plan_id,
        applied_plan=applied_plan_obj,
        all_recovery_plans=analysis.recovery_plans,
        llm_executive_summary=llm_summary,
        llm_team_notification=llm_notification,
        llm_provider_info=llm_provider,
        operator_notes=store_item.get("operator_notes"),
        updated_at=analysis.timestamp
    )

active_delivery_acknowledgements: Dict[str, Dict[str, Any]] = {}

@router.get("/deliveries/affected", response_model=DeliveryPortalResponse)
def get_affected_deliveries_portal(current_user: str = Depends(verify_token)):
    """
    Delivery Management Portal Endpoint.
    Returns affected deliveries, SLA breach risks, priority rankings, and LLM team alerts for Transport Agent reported incidents.
    Strictly sanitizes response to omit operator cost figures or private notes.
    """
    if not active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                wind_speed_mph=active_db_inc.wind_speed_mph,
                precipitation_inches=active_db_inc.precipitation_inches,
                visibility_miles=active_db_inc.visibility_miles,
                temperature_f=active_db_inc.temperature_f,
                road_capacity_reduction_pct=active_db_inc.road_capacity_reduction_pct,
                average_speed_mph=active_db_inc.average_speed_mph,
                normal_speed_mph=active_db_inc.normal_speed_mph,
                active_vehicle_incident=active_db_inc.active_vehicle_incident,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=active_db_inc.reported_by or current_user)

    if not active_plan_store:
        db_acks = repo.get_delivery_acknowledgements()
        return DeliveryPortalResponse(
            status="NO_ACTIVE_INCIDENT",
            disruption_id="NONE",
            disruption_type="NONE",
            location_name="No Active Incident",
            severity_level=0.0,
            updated_at=datetime.now().isoformat(),
            llm_team_notification="No incident has been reported by the Transport Team. All deliveries running on normal baseline schedule.",
            affected_deliveries_count=0,
            at_risk_sla_count=0,
            total_expected_delay_minutes=0.0,
            affected_deliveries=[],
            priority_rankings=[],
            acknowledged_deliveries=db_acks
        )

    disruption_id = list(active_plan_store.keys())[-1]
    store_item = active_plan_store[disruption_id]
    analysis: FullAnalysisResponse = store_item["analysis"]

    disr_input = analysis.disruption_input
    impact = analysis.impact_analysis
    db_acks = repo.get_delivery_acknowledgements()

    NODE_MAP_COORDS = {
        "NODE_MIDTOWN_HUB": [40.7549, -73.9840],
        "NODE_QUEENS_DC": [40.7420, -73.9350],
        "NODE_MANHATTAN_BRIDGE": [40.7090, -73.9900],
        "NODE_BROOKLYN_BRIDGE": [40.7061, -73.9969],
        "NODE_WILLIAMSBURG_BRIDGE": [40.7135, -73.9725],
        "NODE_FDR_DRIVE": [40.7300, -73.9740],
        "NODE_LINCOLN_TUNNEL": [40.7580, -74.0010],
        "NODE_QUEENS_TUNNEL": [40.7445, -73.9680],
        "NODE_BROOKLYN_NAVY": [40.7010, -73.9740],
        "NODE_HARLEM_GATEWAY": [40.8100, -73.9450],
        "NODE_FINANCIAL": [40.7075, -74.0090],
        "NODE_JFK_CARGO": [40.6413, -73.7781]
    }

    loc_node = disr_input.location_node_id
    disrupted_node_coords = NODE_MAP_COORDS.get(loc_node, [40.7090, -73.9900])
    hub_coords = NODE_MAP_COORDS["NODE_MIDTOWN_HUB"]

    disrupted_segment_obj = {
        "u_node": "NODE_MIDTOWN_HUB",
        "v_node": loc_node,
        "location_name": disr_input.location_name,
        "coords": [hub_coords, disrupted_node_coords]
    }

    original_route_obj = {
        "plan_id": "BASELINE_ROUTE",
        "plan_name": "Original Baseline Route",
        "coords": [hub_coords, disrupted_node_coords, NODE_MAP_COORDS["NODE_BROOKLYN_NAVY"], NODE_MAP_COORDS["NODE_FINANCIAL"]]
    }

    plans = analysis.recovery_plans or {}
    plan_a_obj = plans.get("PLAN_A")
    plan_b_obj = plans.get("PLAN_B")

    selected_plan = store_item.get("selected_plan")
    best_plan = selected_plan or (plan_b_obj.model_dump() if plan_b_obj else (plan_a_obj.model_dump() if plan_a_obj else None))

    is_infeasible = (
        disr_input.disruption_type == "no_alternative_blocked" or
        "no alternative" in (disr_input.description or "").lower() or
        (disr_input.location_node_id == "NODE_ISOLATED" and disr_input.severity_level >= 5.0) or
        (best_plan and best_plan.get("optimization_status") == "NO_FEASIBLE_ROUTE")
    )

    if is_infeasible:
        optimization_status = "NO_FEASIBLE_ROUTE"
        infeasibility_reason = "No valid alternative path exists on the remaining network graph. All alternative corridor edges exceed capacity constraints."
        optimized_route_obj = None
    else:
        optimization_status = "FEASIBLE"
        infeasibility_reason = None
        optimized_route_obj = {
            "plan_id": best_plan.get("plan_id", "PLAN_B") if best_plan else "PLAN_B",
            "plan_name": best_plan.get("plan_name", "Fastest Feasible Route") if best_plan else "Fastest Feasible Route",
            "strategy_summary": best_plan.get("strategy_summary", "Optimized reroute excluding blocked corridor") if best_plan else "",
            "total_distance_miles": best_plan.get("total_distance_miles", 0.0) if best_plan else 0.0,
            "total_duration_minutes": best_plan.get("total_duration_minutes", 0.0) if best_plan else 0.0,
            "total_cost_usd": best_plan.get("total_cost_usd", 0.0) if best_plan else 0.0,
            "coords": best_plan.get("route_coords", []) if best_plan else []
        }

    return DeliveryPortalResponse(
        status="ACTIVE",
        disruption_id=disruption_id,
        disruption_type=disr_input.disruption_type,
        location_name=disr_input.location_name,
        severity_level=disr_input.severity_level,
        description=disr_input.description,
        reported_by=disr_input.reported_by,
        updated_at=analysis.timestamp,
        llm_team_notification=analysis.explainability.llm_team_notification,
        affected_deliveries_count=impact.affected_deliveries_count,
        at_risk_sla_count=impact.at_risk_sla_count,
        total_expected_delay_minutes=impact.total_expected_delay_minutes,
        affected_deliveries=impact.affected_deliveries,
        priority_rankings=analysis.priority_rankings,
        acknowledged_deliveries=db_acks,
        disrupted_segment=disrupted_segment_obj,
        original_route=original_route_obj,
        optimized_route=optimized_route_obj,
        all_recovery_plans=plans,
        path_a=plan_a_obj,
        path_b=plan_b_obj,
        optimization_status=optimization_status,
        infeasibility_reason=infeasibility_reason
    )

@router.post("/deliveries/acknowledge", response_model=DeliveryAcknowledgeResponse)
def acknowledge_delivery_endpoint(request: DeliveryAcknowledgeRequest, current_user: str = Depends(verify_token)):
    """
    Enables Delivery Team users to safely acknowledge delivery alert updates with DB persistence.
    """
    ack_dict = repo.record_delivery_acknowledgement(
        delivery_id=request.delivery_id,
        acknowledged_by=current_user,
        notes=request.notes
    )

    repo.record_audit_entry(
        actor_id=current_user,
        actor_role="delivery_team",
        action_type="DELIVERY_ACKNOWLEDGED",
        entity_type="DELIVERY",
        entity_id=request.delivery_id,
        state_after={"notes": request.notes}
    )

    return DeliveryAcknowledgeResponse(
        status="ACKNOWLEDGED",
        delivery_id=request.delivery_id,
        acknowledged_by=current_user,
        timestamp=ack_dict["timestamp"]
    )

@router.post("/recovery/compare", response_model=PlanComparisonResponse)
def compare_recovery_plans_endpoint(
    request: PlanRecommendationRequest,
    current_user: str = Depends(verify_token)
):
    """
    Phase 5 Endpoint: Structured recovery plan comparison and deterministic decision support recommendation.
    Sanitizes operating cost data for non-operator roles.
    Persists recommendation audit trail without automatically accepting plans.
    """
    disruption_id = request.disruption_id
    if disruption_id not in active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc and active_db_inc.id == disruption_id:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=current_user)
        else:
            raise HTTPException(status_code=404, detail="No active incident found. Transport Agent must submit an incident report first.")

    store_item = active_plan_store.get(disruption_id) or active_plan_store[list(active_plan_store.keys())[-1]]
    analysis: FullAnalysisResponse = store_item["analysis"]

    is_operator = ("operator" in current_user.lower() or "admin" in current_user.lower())

    comparison_resp = decision_engine.compare_and_recommend(
        recovery_plans=analysis.recovery_plans,
        policy=request.policy,
        prioritized_deliveries=analysis.priority_rankings,
        disruption_id=disruption_id,
        is_operator=is_operator
    )

    # Persist recommendation in DB audit trail without automatic acceptance
    rec = comparison_resp.recommendation
    repo.record_plan_recommendation(
        disruption_id=disruption_id,
        recommended_plan_id=rec.recommended_plan_id,
        policy_used=rec.policy_used,
        criteria_and_weights=rec.criteria_and_weights,
        reasons=rec.reasons
    )

    repo.record_audit_entry(
        actor_id=current_user,
        actor_role="logistics_operator" if is_operator else "user",
        action_type="RECOMMENDATION_GENERATED",
        entity_type="RECOVERY_PLAN",
        entity_id=disruption_id,
        state_after={"recommended_plan_id": rec.recommended_plan_id, "policy": rec.policy_used}
    )

    return comparison_resp

@router.get("/recovery/recommendation", response_model=PlanRecommendationResponse)
def get_recovery_recommendation_endpoint(
    disruption_id: Optional[str] = None,
    policy: str = "MINIMIZE_COST",
    current_user: str = Depends(verify_token)
):
    """
    Phase 5 Endpoint: Retrieves deterministic recommendation for active disruption with policy parameter.
    """
    if not active_plan_store:
        active_db_inc = repo.get_latest_active_transport_incident()
        if active_db_inc:
            d_input = DisruptionInput(
                disruption_id=active_db_inc.id,
                disruption_type=active_db_inc.disruption_type,
                location_node_id=active_db_inc.location_node_id,
                location_name=active_db_inc.location_name,
                severity_level=active_db_inc.severity_level,
                description=active_db_inc.description or "",
                reported_by=active_db_inc.reported_by
            )
            analyze_disruption(d_input, current_user=current_user)
        else:
            raise HTTPException(status_code=404, detail="No active incident found. Transport Agent must submit an incident report first.")

    d_id = disruption_id or list(active_plan_store.keys())[-1]
    store_item = active_plan_store.get(d_id) or active_plan_store[list(active_plan_store.keys())[-1]]
    analysis: FullAnalysisResponse = store_item["analysis"]

    rec = decision_engine.evaluate_recommendation(
        recovery_plans=analysis.recovery_plans,
        policy=policy,
        prioritized_deliveries=analysis.priority_rankings
    )

    repo.record_plan_recommendation(
        disruption_id=d_id,
        recommended_plan_id=rec.recommended_plan_id,
        policy_used=rec.policy_used,
        criteria_and_weights=rec.criteria_and_weights,
        reasons=rec.reasons
    )

    return rec

# Phase 6 Endpoints: Incident Lifecycle, Cross-Portal Notifications, SSE Streaming, Audit Logs
@router.post("/disruption/{disruption_id}/status", response_model=IncidentStatusUpdateResponse)
def update_disruption_status_endpoint(
    disruption_id: str,
    payload: IncidentStatusUpdateRequest,
    current_user: str = Depends(verify_token),
    authorization: Optional[str] = Header(None)
):
    """
    Incident lifecycle state transition endpoint. Validates permitted transitions and role authorization.
    """
    token_info = get_current_token_info(authorization)
    role = token_info.get("role", "logistics_operator")

    target_status = payload.status.upper()
    if target_status in ["RECOVERY_APPROVED", "RESOLVED"] and role not in ["logistics_operator", "admin"]:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not authorized to set status to '{target_status}'. Operator authorization required."
        )

    try:
        res = repo.update_disruption_status(
            disruption_id=disruption_id,
            new_status=target_status,
            actor_id=current_user,
            actor_role=role
        )
        return IncidentStatusUpdateResponse(
            disruption_id=res["disruption_id"],
            previous_status=res["previous_status"],
            current_status=res["current_status"],
            updated_by=res["updated_by"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status update failure: {str(e)}")

@router.get("/notifications", response_model=NotificationListResponse)
def get_notifications(
    role: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Returns persistent, role-scoped notifications with unread counter.
    """
    token_info = get_current_token_info(authorization) if authorization else {"role": role or "all"}
    user_role = role or token_info.get("role", "all")

    notifs_raw = repo.get_notifications_for_role(user_role)
    notif_items = [NotificationItem(**n) for n in notifs_raw]
    unread_count = sum(1 for n in notif_items if not n.is_read)

    return NotificationListResponse(
        notifications=notif_items,
        unread_count=unread_count
    )

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: str = Depends(verify_token)
):
    """
    Marks a notification as read.
    """
    success = repo.mark_notification_as_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found.")
    return {"status": "SUCCESS", "id": notification_id}

@router.get("/notifications/stream")
async def notifications_stream(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Server-Sent Events (SSE) live updates stream for role-scoped notifications.
    Authenticates connection and streams real-time updates.
    """
    token_info = get_token_info_flexible(authorization, token)
    user_role = token_info.get("role", "all")

    async def event_generator():
        last_seen_id = 0
        while True:
            try:
                notifs = repo.get_notifications_for_role(user_role)
                new_notifs = [n for n in notifs if n["id"] > last_seen_id]
                if new_notifs:
                    last_seen_id = max(n["id"] for n in new_notifs)
                    yield f"event: notification\ndata: {json.dumps(new_notifs)}\n\n"
                else:
                    yield ": keepalive\n\n"
            except Exception as e:
                yield f": error {str(e)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/audit-logs", response_model=AuditLogListResponse)
def get_audit_logs_endpoint(
    limit: int = 50,
    current_user: str = Depends(require_role(["logistics_operator"]))
):
    """
    Returns audit trail history for key operational actions. Restricted to operator role.
    """
    raw_logs = repo.get_audit_logs(limit=limit)
    log_items = [AuditLogItem(**log) for log in raw_logs]
    return AuditLogListResponse(logs=log_items)




