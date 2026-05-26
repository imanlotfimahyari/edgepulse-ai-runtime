from __future__ import annotations

import logging

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.metrics import MODEL_INFO
from app.mqtt_consumer import start_mqtt_consumer
from app.schemas import InferenceRequest, InferenceResponse
from app.service import process_inference_request

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="EdgePulse AI Runtime",
    description="Lightweight edge-AI runtime for simulated industrial and IoT telemetry.",
    version="0.2.0",
)

MODEL_INFO.labels(
    model_name=settings.model_name,
    model_version=settings.model_version,
    model_backend=settings.model_backend,
).set(1)


@app.on_event("startup")
def startup() -> None:
    if settings.mqtt_enabled:
        start_mqtt_consumer()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/readyz")
def readyz() -> dict[str, str | bool]:
    return {
        "status": "ready",
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "model_backend": settings.model_backend,
        "mqtt_enabled": settings.mqtt_enabled,
    }


@app.get("/model/info")
def model_info() -> dict[str, str | float]:
    return {
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "model_backend": settings.model_backend,
        "anomaly_threshold": settings.anomaly_threshold,
    }


@app.post("/infer", response_model=InferenceResponse)
def infer(request: InferenceRequest) -> InferenceResponse:
    return process_inference_request(request, ingestion="http")


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
