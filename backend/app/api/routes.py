from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.schemas import (
    DisruptionInput, DisruptionClassification, FullAnalysisResponse,
    PlanSelectionRequest, PlanSelectionResponse, MLMetricsResponse
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

from app.db.config import engine, USE_POSTGRES, get_db
from app.db.repository import DatabaseRepository
from app.db.seed import seed_database
from app.db.models import (
    DepotModel, RoadSegmentModel, CustomerModel, VehicleModel,
    RouteModel, DisruptionModel, RecoveryPlanModel, PlanSelectionModel
)

from app.api.auth import verify_token

router = APIRouter(prefix="/api")

# Singleton DB Repo
repo = DatabaseRepository()

# In-memory singletons for Phase 1 backend engine (initialized with DB-backed DataLoader)
data_loader = DataLoader(use_db=True)
classifier_service = DisruptionClassifierService()
dependency_graph = LogisticsDependencyGraph(data_loader)
impact_engine = ImpactEngine(data_loader, dependency_graph)
priority_engine = PriorityEngine(data_loader)
recovery_engine = ORToolsRecoveryEngine(data_loader)
explainability_engine = ExplainabilityEngine()

# State store for operator plan selections
active_plan_store: Dict[str, Dict[str, Any]] = {}

@router.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Disruption-Aware Logistics Intelligence Backend",
        "database": "PostgreSQL + PostGIS" if USE_POSTGRES else "SQLite (Spatial PostGIS compatibility mode)",
        "timestamp": datetime.now().isoformat()
    }

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
        # 1. XGBoost Classification
        classification = classifier_service.predict(disruption)

        # Persist Disruption record in DB
        repo.save_disruption(disruption, classification.predicted_class, classification.confidence)

        # 2. Impact Engine (using NetworkX dependency graph traversal)
        impact = impact_engine.evaluate_impact(disruption, classification)

        # 3. Priority Engine (Dynamic 0-100 SLA scoring)
        priorities = priority_engine.rank_affected_deliveries(impact.affected_deliveries)

        # 4. OR-Tools Recovery Engine (Plan A, Plan B, Plan C)
        recovery_plans = recovery_engine.generate_recovery_plans(disruption, priorities)

        # Persist Recovery Plans in DB
        repo.save_recovery_plans(disruption.disruption_id, recovery_plans)

        # 5. Explainability Engine (SHAP + Rule-based reasons)
        explanation = explainability_engine.generate_report(disruption, classification, impact, recovery_plans)

        response = FullAnalysisResponse(
            disruption_input=disruption,
            classification=classification,
            impact_analysis=impact,
            priority_rankings=priorities,
            recovery_plans=recovery_plans,
            explainability=explanation,
            timestamp=datetime.now().isoformat()
        )

        active_plan_store[disruption.disruption_id] = {
            "analysis": response,
            "selected_plan": None
        }

        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"End-to-end analysis failure: {str(e)}")

@router.post("/recovery/accept", response_model=PlanSelectionResponse)
def accept_recovery_plan(request: PlanSelectionRequest, current_user: str = Depends(verify_token)):
    disruption_id = request.disruption_id
    if disruption_id not in active_plan_store:
        scenario = REPRODUCIBLE_SCENARIOS.get("NYC_BLIZZARD")
        analyze_disruption(scenario, current_user=current_user)

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

    return PlanSelectionResponse(
        status="ACCEPTED",
        message=f"Operator approved plan '{selected_plan.plan_name}'. Route updates dispatched to fleet.",
        disruption_id=disruption_id,
        applied_plan_id=selected_id,
        active_plan=selected_plan,
        updated_at=datetime.now().isoformat()
    )

@router.post("/recovery/modify", response_model=PlanSelectionResponse)
def modify_recovery_plan(request: PlanSelectionRequest, current_user: str = Depends(verify_token)):
    disruption_id = request.disruption_id
    if disruption_id not in active_plan_store:
        scenario = REPRODUCIBLE_SCENARIOS.get("NYC_BLIZZARD")
        analyze_disruption(scenario, current_user=current_user)

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
