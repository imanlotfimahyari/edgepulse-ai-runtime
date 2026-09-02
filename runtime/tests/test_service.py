from __future__ import annotations

import pytest
from app import service
from app.schemas import InferenceRequest


def test_process_inference_request(monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "model_name", "test-model")
    monkeypatch.setattr(service.settings, "model_version", "1.0.0")
    monkeypatch.setattr(service.settings, "model_backend", "rule-based")

    monkeypatch.setattr(
        service,
        "run_inference",
        lambda features: ("normal", 0.2, 0.8),
    )

    request = InferenceRequest(
        device_id="device-001",
        device_type="vibration_sensor",
        features=[0.1, 0.2, 0.3],
    )

    response = service.process_inference_request(
        request,
        ingestion="http",
    )

    assert response.device_id == "device-001"
    assert response.device_type == "vibration_sensor"
    assert response.model_name == "test-model"
    assert response.model_version == "1.0.0"
    assert response.model_backend == "rule-based"
    assert response.prediction == "normal"
    assert response.anomaly_score == 0.2
    assert response.confidence == 0.8
    assert response.latency_ms >= 0


def test_process_inference_request_propagates_inference_error(
    monkeypatch,
) -> None:
    def fail_inference(features: list[float]) -> tuple[str, float, float]:
        raise RuntimeError("inference failed")

    monkeypatch.setattr(
        service,
        "run_inference",
        fail_inference,
    )

    request = InferenceRequest(
        device_id="device-001",
        device_type="vibration_sensor",
        features=[0.1, 0.2],
    )

    with pytest.raises(RuntimeError, match="inference failed"):
        service.process_inference_request(
            request,
            ingestion="http",
        )
