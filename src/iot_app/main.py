from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional
import os
import random
from datetime import datetime, timezone

app = FastAPI()

# ── Auth ──────────────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)
EXPECTED_TOKEN = os.getenv("API_TOKEN", "local-dev-token")

PROBLEM_401 = {
    "type": "https://httpstatuses.com/401",
    "title": "Unauthorized",
    "status": 401,
    "detail": "Unauthorized access - Invalid or missing token"
}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials or credentials.credentials != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail=PROBLEM_401)
    return credentials.credentials

# ── Custom 422 handler (RFC 7807 Problem Details) ────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://httpstatuses.com/422",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": str(exc.errors())
        }
    )

# ── Custom 401 handler ────────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://httpstatuses.com/{exc.status_code}",
            "title": "Error",
            "status": exc.status_code,
            "detail": exc.detail
        }
    )

# ── In-memory store ───────────────────────────────────────────────────────────
readings_db: dict = {}
_counter = 0

def generate_reading_id() -> str:
    global _counter
    _counter += 1
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"R-{date_str}-{_counter:04d}"

# ── Schemas ───────────────────────────────────────────────────────────────────
class ReadingCreate(BaseModel):
    device_id: str
    metric: Optional[str] = "temperature"
    value: float
    unit: Optional[str] = "celsius"
    timestamp: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def value_must_be_numeric(cls, v):
        if isinstance(v, str):
            raise ValueError("value must be a number, not a string")
        return v

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "iot-readings-service",
        "version": "0.1.0"
    }


@app.post("/readings", status_code=201, dependencies=[Depends(verify_token)])
def create_reading(reading: ReadingCreate, response: Response):
    if reading.value > 80:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://httpstatuses.com/422",
                "title": "Unprocessable Entity",
                "status": 422,
                "detail": "Temperature value exceeds maximum allowed (80)"
            }
        )

    reading_id = generate_reading_id()
    ts = reading.timestamp or datetime.now(timezone.utc).isoformat()

    record = {
        "reading_id": reading_id,
        "device_id": reading.device_id,
        "metric": reading.metric or "temperature",
        "value": reading.value,
        "unit": reading.unit or "celsius",
        "timestamp": ts,
        "accepted": True,
        "warning": None
    }

    if reading.value == 80:
        record["warning"] = "High temperature threshold reached"
        response.headers["X-Warning"] = "high-temperature"

    readings_db[reading_id] = record
    return record


@app.get("/readings/latest", dependencies=[Depends(verify_token)])
def get_latest_readings(device_id: Optional[str] = None, limit: int = 10):
    items = list(readings_db.values())
    if device_id:
        items = [r for r in items if r["device_id"] == device_id]
    items = items[-limit:]
    return {"items": items}


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_token)])
def get_reading(reading_id: str):
    record = readings_db.get(reading_id)
    if not record:
        raise HTTPException(status_code=404, detail="Reading not found")
    return record