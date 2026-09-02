from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from app import inference
from app.config import settings
from app.metrics import MODEL_INFO
from app.model_manifest import load_model_manifest
from app.mqtt_consumer import start_mqtt_consumer
from app.schemas import InferenceRequest, InferenceResponse
from app.service import process_inference_request
from fastapi import FastAPI, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

logging.basicConfig(level=logging.INFO)

runtime_ready = False
readiness_error: str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global runtime_ready, readiness_error

    try:
        if settings.model_backend == "onnx":
            inference._get_onnx_session()

        if settings.mqtt_enabled:
            start_mqtt_consumer()

        runtime_ready = True
        readiness_error = None

    except Exception as exc:
        runtime_ready = False
        readiness_error = str(exc)
        logging.exception("Runtime initialization failed")

    yield

    runtime_ready = False


app = FastAPI(
    title="EdgePulse AI Runtime",
    description="Lightweight edge-AI runtime for simulated industrial and IoT telemetry.",
    version="0.9.0",
    lifespan=lifespan,
)


MODEL_INFO.labels(
    model_name=settings.model_name,
    model_version=settings.model_version,
    model_backend=settings.model_backend,
).set(1)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/readyz")
def readyz(response: Response) -> dict[str, object]:
    if not runtime_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "not-ready",
            "model_name": settings.model_name,
            "model_version": settings.model_version,
            "model_backend": settings.model_backend,
            "mqtt_enabled": settings.mqtt_enabled,
            "error": readiness_error or "runtime initialization incomplete",
        }

    return {
        "status": "ready",
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "model_backend": settings.model_backend,
        "mqtt_enabled": settings.mqtt_enabled,
    }


@app.get("/model/info")
def model_info() -> dict[str, Any]:
    return {
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "model_backend": settings.model_backend,
        "anomaly_threshold": settings.anomaly_threshold,
        "model_manifest": load_model_manifest(),
    }


@app.post("/infer", response_model=InferenceResponse)
def infer(request: InferenceRequest) -> InferenceResponse:
    return process_inference_request(request, ingestion="http")


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
