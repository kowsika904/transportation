# HACKNEXT'26 PS02 — ANTIGRAVITY MASTER BUILD PLAN

## Project
Disruption-Aware Logistics Planning

## Fixed Architecture

```text
REAL-WORLD DATA
        │
   ┌────┼─────┐
   ▼    ▼     ▼
  TLC  OSMnx  NOAA
 Trips Road   Weather
       Map
   │    │     │
   └────┼─────┘
        ▼
 DATA PROCESSING
        │
        ▼
 DISRUPTION INPUT
        │
        ▼
 DISRUPTION CLASSIFIER
       XGBoost
        │
        ▼
 DEPENDENCY GRAPH
     NetworkX
        │
        ▼
  IMPACT ENGINE
        │
   ┌────┼────┐
   ▼    ▼    ▼
Routes Vehicles Deliveries
   │    │    │
   └────┼────┘
        ▼
 PRIORITY ENGINE
        │
        ▼
 RECOVERY ENGINE
     OR-Tools
        │
   ┌────┼────┐
   ▼    ▼    ▼
Plan A Plan B Plan C
   │    │    │
   └────┼────┘
        ▼
 EXPLAINABILITY
     SHAP +
 Rule-based reasons
        │
        ▼
 OPERATOR DASHBOARD
        │
  ACCEPT / MODIFY
        │
        ▼
 UPDATED PLAN
```

## Fixed Technology Stack

- Real-world movement data: NYC TLC Trip Records
- Road network: OpenStreetMap + OSMnx
- Weather/disruption data: NOAA historical weather
- Routing benchmark: CVRPLIB / VRP instances
- ML: XGBoost
- Dependency graph: NetworkX
- Recovery optimization: Google OR-Tools
- Explainability: SHAP + rule-based reasons
- Backend: Python FastAPI
- Database: PostgreSQL + PostGIS
- Data processing: Pandas + GeoPandas
- Frontend: React + Vite
- Maps: Leaflet + OpenStreetMap
- Visualization: Plotly
- Deployment: Docker

Do not replace the above stack unless a dependency is technically incompatible and the change is unavoidable.

## Core Product Rule

This is NOT an ETA-only or prediction-only application.

The workflow must remain:

Disruption
→ Understand disruption
→ Trace dependencies
→ Calculate impact
→ Prioritize affected operations
→ Generate recovery plans
→ Explain the plans/reasons
→ Operator accepts or modifies
→ Updated plan

The system must not automatically make an irreversible operational decision without operator approval.

## ML Requirement

Use XGBoost for the disruption-classification component.

The implementation must include:
- reproducible preprocessing
- train/validation/test separation
- saved model artifact
- consistent feature preprocessing at inference
- class-wise metrics
- confusion matrix
- accuracy
- precision
- recall
- F1-score
- prediction endpoint
- test cases for inference

Do not claim 100% accuracy or "perfect" prediction without measured evidence. The goal is a correctly working, reproducible ML pipeline with honest evaluation.

## Data Requirement

Use:
- NYC TLC trip records for real movement/travel patterns
- OpenStreetMap/OSMnx for road-network structure
- NOAA historical weather for weather conditions
- CVRPLIB/VRP instances for vehicle/customer/capacity/time-window structures
- A structured disruption scenario layer for road closures, accidents, weather disruptions, vehicle breakdowns and delivery requirement changes

Do not pretend TLC alone contains complete logistics entities such as vehicle IDs, delivery IDs, customers, capacities and delivery deadlines. Build the application's logistics scenario structures from the appropriate data sources.

## Phase Structure

### PHASE 1 — BACKEND + AI/ML ENGINE

Goal: Build the complete backend intelligence without the final frontend.

Implement:
1. Project/backend structure with FastAPI.
2. Data ingestion and preprocessing modules.
3. XGBoost disruption classifier.
4. ML evaluation and saved model.
5. NetworkX dependency graph.
6. Impact Engine for routes, vehicles and deliveries.
7. Priority Engine.
8. OR-Tools Recovery Engine.
9. Plan A / Plan B / Plan C generation.
10. SHAP explanations and rule-based reasons.
11. Backend API endpoints for the above workflow.
12. Automated tests for core calculations and API behavior.

Backend flow:

```text
Data
→ Processing
→ Disruption Input
→ XGBoost
→ NetworkX
→ Impact Engine
→ Priority Engine
→ OR-Tools
→ Plan A/B/C
→ SHAP + Rule Reasons
→ API response
```

Acceptance criteria:
- Backend starts successfully.
- A structured disruption can be submitted.
- The classifier returns a disruption class and measured confidence/probability.
- Dependency graph identifies affected entities.
- Impact engine returns affected routes/vehicles/deliveries.
- Priority engine returns transparent priority scores.
- OR-Tools produces feasible recovery plans.
- Explanations are returned with results.
- Tests pass.

### PHASE 2 — DATABASE

Goal: Persist the exact entities used by the existing backend workflow.

Use PostgreSQL + PostGIS.

Create only the required data model for:
- routes
- vehicles
- deliveries
- customers
- schedules/time windows
- disruptions
- dependency relationships
- recovery plans
- plan selections/updates
- ML prediction/evaluation records where required by the existing workflow

Integrate the database with FastAPI.

Do not redesign the business workflow.

Acceptance criteria:
- Database starts reliably.
- Tables and relationships are created through migrations.
- Seed/demo data can be loaded.
- Backend reads/writes the required entities.
- Geospatial route/location data is stored correctly.
- Existing Phase 1 intelligence works using database-backed data.

### PHASE 3 — FRONTEND

Goal: Build the final operator dashboard.

Use:
- React
- Vite
- Leaflet + OpenStreetMap
- Plotly where needed

UI direction:
- Attractive, modern, professional logistics control-room style.
- Strong visual hierarchy.
- Clear disruption status.
- Clear impact visualization.
- Interactive map for affected routes.
- Route/vehicle/delivery impact panels.
- Priority indicators.
- Plan A / Plan B / Plan C comparison.
- Explainability panel.
- ACCEPT / MODIFY actions.
- Updated plan view.

Do NOT add unrelated:
- chatbots
- generic analytics pages
- authentication flows unless required for the hackathon demo
- social features
- unnecessary AI features
- unrelated prediction dashboards
- unrelated pages

The frontend must represent the existing backend workflow exactly.

Acceptance criteria:
- User can enter/select a disruption scenario.
- Dashboard displays the resulting impact.
- Map displays relevant routes and affected elements.
- Priority results are visible.
- Plan A/B/C are clearly comparable.
- Explanation is visible.
- Operator can accept or modify a recovery plan.
- Updated plan is reflected in the UI.

## README Requirement

The project's README must contain:
1. Project title
2. Problem understanding
3. Core workflow
4. Architecture
5. Technology stack
6. Data sources
7. Phase structure
8. ML evaluation section
9. How to run backend
10. How to run database
11. How to run frontend
12. Demo workflow
13. Project limitations

Keep README factual. Do not claim unsupported accuracy, live data, or production readiness.

## Antigravity Execution Rules

- Execute one phase at a time.
- Do not silently skip a failed component.
- Do not invent datasets that do not exist.
- Do not hardcode fake ML accuracy.
- Do not fabricate model performance.
- Do not replace XGBoost, NetworkX, OR-Tools, SHAP, FastAPI, PostgreSQL/PostGIS, React/Vite, OSMnx or the stated data sources without a technical reason.
- Keep modules separated so each phase can be tested independently.
- Before moving to the next phase, verify the current phase works.
- Update README.md after each completed phase with only verified information.
- Keep the implementation focused strictly on the supplied architecture.

## Definition of Done

The project is complete only when:

```text
REAL DATA
   ↓
DATA PROCESSING
   ↓
DISRUPTION INPUT
   ↓
XGBOOST CLASSIFICATION
   ↓
NETWORKX DEPENDENCY GRAPH
   ↓
IMPACT ENGINE
   ↓
PRIORITY ENGINE
   ↓
OR-TOOLS RECOVERY
   ↓
PLAN A / B / C
   ↓
SHAP + RULE EXPLANATION
   ↓
REACT OPERATOR DASHBOARD
   ↓
ACCEPT / MODIFY
   ↓
UPDATED PLAN
```

Every stage must be demonstrable.
