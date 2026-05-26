from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    device_id: str = Field(..., examples=["device-vibration-001"])
    device_type: str = Field(default="vibration_sensor", examples=["vibration_sensor"])
    payload_type: str = Field(default="vibration", examples=["vibration"])
    features: list[float] = Field(
        ..., min_length=1, examples=[[0.12, 0.14, 0.19, 0.25, 0.22]]
    )
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None


class InferenceResponse(BaseModel):
    device_id: str
    device_type: str
    model_name: str
    model_version: str
    model_backend: str
    prediction: Literal["normal", "anomaly"]
    anomaly_score: float
    confidence: float
    latency_ms: float
