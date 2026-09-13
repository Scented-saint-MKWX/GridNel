from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class OperatorInfo(BaseModel):
    name: str
    badge_id: str
    clearance: str
    department: str

class LoginResponse(BaseModel):
    status: str
    token: str
    operator: OperatorInfo

AUTHORIZED_ACCOUNTS = {
    "officer.sharma@sentinel.gov": {
        "password": "Sentinel#Tactical99",
        "name": "Inspector V. Sharma",
        "badge_id": "SG-OP-709",
        "clearance": "Tier-1 Tactical Clearance",
        "department": "Metropolitan ANPR Surveillance Command"
    },
    "commander@sentinel.gov": {
        "password": "Sentinel#Secure99",
        "name": "Commander A. Rathore",
        "badge_id": "SG-HQ-001",
        "clearance": "Executive Command Clearance",
        "department": "Central Law Enforcement Operations"
    }
}

@router.post("/auth/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    username = creds.username.strip().lower()
    account = AUTHORIZED_ACCOUNTS.get(username)
    if not account or account["password"] != creds.password:
        raise HTTPException(
            status_code=401,
            detail="Access Denied: Invalid credentials or insufficient clearance level."
        )
    
    return {
        "status": "authorized",
        "token": "sentinel-tactical-token-709",
        "operator": {
            "name": account["name"],
            "badge_id": account["badge_id"],
            "clearance": account["clearance"],
            "department": account["department"]
        }
    }

