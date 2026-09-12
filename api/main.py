from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

from fastapi import FastAPI, Header, HTTPException

from .schemas import DataBlock
from .ingest import ingest_block


app = FastAPI(
    title="SentinelGrid Central Server"
)


@app.get("/healthz")
def health_check():
    return {
        "status": "ok",
        "service": "sentinelgrid-api"
    }


@app.post("/ingest")
def ingest(
    block: DataBlock,
    x_api_key: str | None = Header(default=None)
):

    # Check that the fog supplied an API key
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing fog API key"
        )

    # Pass the validated DataBlock and API key
    # to the ingestion logic
    return ingest_block(block, x_api_key)
