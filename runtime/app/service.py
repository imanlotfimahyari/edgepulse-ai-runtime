from __future__ import annotations

import time

from app.config import settings
from app.inference import run_inference
from app.metrics import (
    DEVICE_MESSAGES,
    INFERENCE_ERRORS,
    INFERENCE_LATENCY,
    INFERENCE_REQUESTS,
)
from app.schemas import InferenceRequest, InferenceResponse


def process_inference_request(
    request: InferenceRequest,
    ingestion: str,
) -> InferenceResponse:
    start_time = time.perf_counter()

    try:
        DEVICE_MESSAGES.labels(
            device_type=request.device_type,
            ingestion=ingestion,
        ).inc()

        prediction, anomaly_score, confidence = run_inference(request.features)

        latency_seconds = time.perf_counter() - start_time

        INFERENCE_LATENCY.labels(
            device_type=request.device_type,
            model_backend=settings.model_backend,
            ingestion=ingestion,
        ).observe(latency_seconds)

        INFERENCE_REQUESTS.labels(
            device_type=request.device_type,
            prediction=prediction,
            model_backend=settings.model_backend,
            ingestion=ingestion,
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
            ingestion=ingestion,
        ).inc()
        raise
