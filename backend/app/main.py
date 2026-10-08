from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="Disruption-Aware Logistics Intelligence API",
    description="HACKNEXT'26 PS02 - End-to-end backend combining XGBoost classification, NetworkX dependency graphs, Impact & Priority engines, and Google OR-Tools recovery optimization.",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "message": "Disruption-Aware Logistics Planning API is operational",
        "docs": "/docs",
        "health": "/api/health",
        "scenarios": "/api/scenarios"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
