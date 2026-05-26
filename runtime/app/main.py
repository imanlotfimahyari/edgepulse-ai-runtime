from __future__ import annotations

import time

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.inference import run_inference
from app.metrics import (
    DEVICE_MESSAGES,
    INFERENCE_ERRORS,
    INFERENCE_LATENCY,
    INFERENCE_REQUESTS,
    MODEL_INFO,
)
from app.schemas import InferenceRequest, InferenceResponse

app = FastAPI(
    title="EdgePulse AI Runtime",
    description="Lightweight edge-AI runtime for simulated industrial and IoT telemetry.",
    version="0.1.0",
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
def readyz() -> dict[str, str]:
    return {
        "status": "ready",
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "model_backend": settings.model_backend,
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
    start_time = time.perf_counter()

    try:
        DEVICE_MESSAGES.labels(device_type=request.device_type).inc()

        prediction, anomaly_score, confidence = run_inference(request.features)

        latency_seconds = time.perf_counter() - start_time
        INFERENCE_LATENCY.labels(
            device_type=request.device_type,
            model_backend=settings.model_backend,
        ).observe(latency_seconds)

        INFERENCE_REQUESTS.labels(
            device_type=request.device_type,
            prediction=prediction,
            model_backend=settings.model_backend,
        ).inc()

        return InferenceResponse(
            device_id=request.device_id,
            device_type=request.device_type,
            model_name=settings.model_name,
            model_version=settings.model_version,
            model_backend=settings.model_backend,
            prediction=prediction,
            anomaly_score=anomaly_score,
            confidence=confidence,
            latency_ms=round(latency_seconds * 1000, 3),
        )

    except Exception:
        INFERENCE_ERRORS.labels(
            device_type=request.device_type,
            model_backend=settings.model_backend,
        ).inc()
        raise


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
