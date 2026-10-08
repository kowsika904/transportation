  # ANTIGRAVITY MASTER PROMPT

You are the coding agent for our HACKNEXT'26 PS02 project: **Disruption-Aware Logistics Planning**.

Read and follow `ANTIGRAVITY_MASTER_PLAN.md` as the single project specification.

IMPORTANT:
- Do not redesign the architecture.
- Do not add unrelated features.
- Do not turn this into an ETA-only or prediction-only project.
- Use the exact workflow:
  Disruption → Understand → Dependency Graph → Impact → Priority → Recovery Plans → Explainability → Operator Dashboard → Accept/Modify → Updated Plan.
- Use the exact requested stack:
  NYC TLC + OpenStreetMap/OSMnx + NOAA + CVRPLIB/VRP instances, XGBoost, NetworkX, OR-Tools, SHAP + rule-based reasons, FastAPI, PostgreSQL/PostGIS, React + Vite, Leaflet/OpenStreetMap, Plotly, Docker.
- The final frontend must be attractive and innovative, but must contain only UI needed for the supplied workflow.
- Do not invent accuracy values. Train and evaluate the XGBoost model properly and show real metrics.
- Do not claim perfect accuracy. Make the prediction pipeline reproducible and testable.
- Keep the human operator in control of ACCEPT/MODIFY.
- Update README.md with the verified architecture and workflow.

## PHASE EXECUTION

Start with **PHASE 1 — BACKEND + AI/ML ENGINE** only.

Do not start Phase 2 or Phase 3 until Phase 1 is working and tested.

For Phase 1:
1. Create the FastAPI backend.
2. Create clean modules for data processing, XGBoost classifier, NetworkX dependency graph, impact engine, priority engine, OR-Tools recovery engine and explainability.
3. Implement the data interfaces for TLC, OSMnx, NOAA and CVRPLIB/VRP data.
4. Create the structured disruption scenario layer needed by the architecture.
5. Train/evaluate XGBoost with proper train/validation/test handling.
6. Save the trained model and preprocessing artifacts.
7. Expose the required API endpoints.
8. Test each component.
9. Run an end-to-end backend demo using a reproducible disruption scenario.
10. Update README.md with only verified Phase 1 information.

When Phase 1 is complete, stop and report:
- files created/changed
- commands to run
- model metrics actually obtained
- tests passed
- any real limitation/blocker

Then wait for my instruction before Phase 2.

For Phase 2:
- integrate PostgreSQL + PostGIS into the existing backend without changing the workflow.
- create migrations and seed data.
- verify Phase 1 still works with database-backed data.
- update README.md.
- stop and report.

For Phase 3:
- create the final React + Vite operator dashboard.
- use Leaflet/OpenStreetMap for the logistics map and Plotly only where useful.
- visually emphasize disruption, impact, priority, Plan A/B/C, explanations and ACCEPT/MODIFY.
- do not add unrelated pages/features.
- connect to the actual backend APIs.
- test the complete workflow.
- update README.md.
- stop and report.

## QUALITY RULE

If a dataset or external service is unavailable, do not fake it silently. Create a clearly marked local demo/sample input only where the architecture requires it, and keep the interface ready for the real source.

Begin with Phase 1 only.
