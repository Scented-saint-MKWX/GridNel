from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import your modular routers and scripts
from . import tracking, alerts, analytics
from .ingest import ingest_block
from .schemas import DataBlock

app = FastAPI(title="SentinelGrid API", description="Hackathon MVP Backend")

# Essential for the Next.js frontend to bypass browser CORS blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo purposes, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the separate feature files
app.include_router(tracking.router, tags=["Tracking"])
app.include_router(alerts.router, tags=["Alerts"])
app.include_router(analytics.router, tags=["Analytics"])

# The high-speed edge ingestion endpoint
@app.post("/ingest", tags=["Ingestion"])
def ingest_data(block: DataBlock, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    # Strip "Bearer " if the fog node sends it in standard format
    api_key = authorization.replace("Bearer ", "")
    
    # Pass to the Redis ingestion logic we finalized earlier
    return ingest_block(block, api_key)