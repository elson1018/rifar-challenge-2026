from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class PredictRequest(BaseModel):
    rainfall_mm: float = Field(..., ge=0, description="Rainfall in millimetres (≥ 0)")
    upstream_level_m: float = Field(..., ge=0, description="Upstream river level in metres (≥ 0)")

class SensorRequest(BaseModel):
    water_level_m: float = Field(..., ge=0, description="Live sensor water level reading in metres")
    rainfall_mm: Optional[float] = Field(None, ge=0, description="Optional live sensor rainfall reading in mm")

class PredictResponse(BaseModel):
    rainfall_mm: float
    upstream_level_m: float
    predicted_water_level_m: float
    alert: Dict[str, Any]

class SensorResponse(BaseModel):
    water_level_m: float
    alert: Dict[str, Any]

class LiveStatusResponse(BaseModel):
    water_level_m: float
    rainfall_mm: float
    predicted_level_m: float
    alert: Dict[str, Any]
