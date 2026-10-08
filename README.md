# Disruption-Aware Logistics Planning
**HACKNEXT'26 PS02 — Master Build System**

## 1. Problem Understanding
Modern logistics operations are highly vulnerable to real-world disruptions (e.g., severe snowstorms, emergency bridge closures, vehicle engine failures, and major traffic accidents). Standard routing systems focus only on static ETAs or baseline predictions. When a disruption hits, operators lack an automated end-to-end intelligence system that:
1. Classifies the severity and nature of the disruption using ML.
2. Traces structural dependencies across complex transport networks.
3. Quantifies cascading operational impacts on routes, vehicles, and customer SLAs.
4. Dynamically prioritizes affected deliveries based on time windows, perishability, and financial risk.
5. Optimizes multi-option recovery routing (Plan A: Minimal Cost, Plan B: Fast Recovery, Plan C: SLA Protection) while keeping the human operator in control (ACCEPT / MODIFY).

## 2. Core Workflow
The application strictly follows the required operational control loop:

```text
Disruption Input 
  → Understand & Classify (XGBoost + SHAP)
  → Dependency Graph Traversal (NetworkX)
  → Quantify Operational Impact (Impact Engine)
  → Dynamic SLA & Priority Ranking (Priority Engine)
  → Multi-Option Recovery Generation (Google OR-Tools VRP)
  → Explainability (SHAP + Rule-Based Trade-offs)
  → Persistent Database Storage (PostgreSQL 17 + PostGIS 3.6)
  → Human Operator Control Center (React + Vite + Leaflet)
  → Operator Acceptance / Parameter Modification
  → Updated Operational Dispatch
```

## 3. Fixed Architecture
```text
REAL-WORLD DATA (NYC TLC Trips, OSMnx Road Map, NOAA Weather, CVRPLIB VRP Instances)
        │
        ▼
  DATABASE STORAGE (PostgreSQL 17 + PostGIS 3.6)
        │
        ▼
  DATA PROCESSING & SCENARIOS
        │
        ▼
  DISRUPTION CLASSIFIER (XGBoost + SHAP)
        │
        ▼
  DEPENDENCY GRAPH (NetworkX)
        │
        ▼
   IMPACT ENGINE (Routes, Vehicles, Deliveries)
        │
        ▼
  PRIORITY ENGINE (0-100 Dynamic SLA Scoring)
        │
        ▼
  RECOVERY ENGINE (Google OR-Tools VRP Solver)
        ├── Plan A: Minimal Cost Reroute
        ├── Plan B: Minimum Time / Fast Recovery
        └── Plan C: Maximum SLA Protection
        │
        ▼
  EXPLAINABILITY ENGINE (SHAP Feature Drivers + Rule Reasons)
        │
        ▼
  OPERATOR DASHBOARD (React + Vite + Leaflet OpenStreetMap)
        │
        ▼
  OPERATOR DECISION (Accept / Modify Plan)
        │
        ▼
  PERSISTENT RECOVERY PLAN & SELECTION STORE (PostgreSQL / PostGIS)
```

## 4. Fixed Technology Stack
- **Real-world movement data**: NYC TLC Trip Records (speed ratio benchmarks across NYC zones)
- **Road network topology**: OpenStreetMap + OSMnx network graphs
- **Weather & environmental data**: NOAA historical weather data
- **Logistics benchmark structure**: CVRPLIB / VRP problem instances
- **ML Classifier**: XGBoost Multiclass Classifier + SHAP Explainability
- **Dependency Graph**: NetworkX Graph
- **Recovery Optimization**: Google OR-Tools (Vehicle Routing Problem solver)
- **Database Engine**: PostgreSQL 17.11 + PostGIS 3.6.2 (GeoAlchemy2 spatial `Geometry` columns, WGS 84 / `EPSG:4326`)
- **Backend API**: Python FastAPI + Uvicorn + SQLAlchemy + Alembic
- **Frontend Dashboard**: React + Vite + Leaflet + OpenStreetMap
- **Data processing**: Pandas, NumPy, Scikit-Learn

## 5. Phase Structure
- **Phase 1 — Backend + AI/ML Engine** *(Completed & Verified)*
- **Phase 2 — Database Integration** *(Completed & Verified)*
- **Phase 3 — Operator Dashboard Frontend** *(Completed & Verified)*
  - Modern hackathon-quality Operations Control Center UI (`frontend/src/`).
  - Interactive Leaflet OpenStreetMap visualizing depots, vehicles, customers, disruption location, and recovery route paths.
  - Operational Impact Chain displaying cascade metrics (affected routes, vehicles, deliveries, SLA risks).
  - SLA Priority Ranking table (0-100 score, tier badges, perishability, item value).
  - Side-by-side OR-Tools Recovery Alternatives (Plan A, Plan B, Plan C) with comparative metrics matrix.
  - SHAP feature attributions bar chart & rule-based decision explanation panel.
  - Human Operator Controls (`[ ACCEPT PLAN ]` and `[ CUSTOMIZE & ACCEPT ]`) updating live database state.
  - Updated operations view showing closed-loop dispatch confirmation.

## 6. Verified ML Evaluation Metrics (XGBoost)
- **Accuracy**: `98.33%`
- **Macro Precision**: `0.9736`
- **Macro Recall**: `0.9485`
- **Macro F1-Score**: `0.9584`

| Disruption Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **STANDARD_FLOW** | 1.0000 | 1.0000 | 1.0000 | 60 |
| **SEVERE_CONGESTION** | 0.9791 | 1.0000 | 0.9894 | 187 |
| **ROAD_CLOSURE** | 1.0000 | 0.9091 | 0.9524 | 33 |
| **SEVERE_WEATHER** | 1.0000 | 0.8333 | 0.9091 | 12 |
| **VEHICLE_BREAKDOWN** | 0.8889 | 1.0000 | 0.9412 | 8 |

## 7. How to Run the Complete System

### Step 1: Database Setup & Seed
```bash
# Set database environment variable
$env:DATABASE_URL="postgresql://postgres:1215@localhost:5432/transportation_db"

# Seed reproducible demo dataset into PostgreSQL
cd backend
python -m app.db.seed
```

### Step 2: Start Backend Server
```bash
# Start FastAPI backend
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Health Check: `http://127.0.0.1:8000/api/health`
- DB Status: `http://127.0.0.1:8000/api/db/status`
- Swagger OpenAPI Docs: `http://127.0.0.1:8000/docs`

### Step 3: Start React Frontend Dashboard
```bash
# Start Vite development server
cd frontend
npm run dev
```
- Dashboard URL: `http://localhost:5173` (or as output by Vite)

## 8. End-to-End Demo Workflow
1. **Open Dashboard**: Open `http://localhost:5173`. Header shows live API and PostgreSQL connection status.
2. **Select Scenario**: Choose a scenario (`NYC Blizzard`, `Manhattan Bridge Closure`, `Vehicle Breakdown`, etc.) in the Disruption Control panel.
3. **Analyze Impact**: Click **"ANALYZE DISRUPTION IMPACT"**.
   - XGBoost classifies the disruption and displays confidence.
   - Leaflet map plots disruption pin, affected nodes, depots, vehicles, and customer SLA risk markers.
   - Impact Chain displays cascade metrics (+102.6 mins total delay, affected routes/vehicles).
   - Priority Ranking ranks deliveries by 0-100 SLA score (e.g. Apex Medical Supplies Hub marked `CRITICAL`).
4. **Compare Recovery Plans**: Inspect side-by-side Plan A (Minimal Cost), Plan B (Minimum Time), and Plan C (Maximum SLA Protection) cards and comparison table.
5. **Inspect Explainability**: View SHAP feature drivers bar chart (`Road Capacity Reduction`, `Severity Level`) and rule-based system reasons.
6. **Accept / Modify Plan**: Click **"ACCEPT & DISPATCH PLAN"** or enter custom duration overrides and click **"CONFIRM CUSTOMIZATIONS"**.
7. **View Updated Dispatch**: Map updates with bright green recovery route overlay, and decision persistence is confirmed in PostgreSQL.
