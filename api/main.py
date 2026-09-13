import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import tracking, alerts, analytics, auth
from .ingest import ingest_block
from .schemas import DataBlock

app = FastAPI(title="SentinelGrid API", description="Smart City Traffic Analytics Platform")

# CORS configured for browser dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature Routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(tracking.router, tags=["Tracking"])
app.include_router(alerts.router, tags=["Alerts"])
app.include_router(analytics.router, tags=["Analytics"])

# Edge Ingestion Endpoint
@app.post("/ingest", tags=["Ingestion"])
def ingest_data(block: DataBlock, authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API Key")
    api_key = authorization.replace("Bearer ", "").strip()
    return ingest_block(block, api_key)

# Frontend UI Mounting
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
FRONTEND_HTML = os.path.join(FRONTEND_DIR, "index.html")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    if os.path.exists(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML)
    return {"message": "SentinelGrid API Active. Visit /docs for Swagger UI."}

if os.path.exists(FRONTEND_DIR):
    app.mount("/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")