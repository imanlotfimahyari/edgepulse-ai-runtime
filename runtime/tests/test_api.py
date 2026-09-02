from __future__ import annotations

import pytest
from app.main import app, settings
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "mqtt_enabled", False)

    with TestClient(app) as test_client:
        yield test_client


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert "service" in body


def test_readyz(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ready"
    assert "model_name" in body
    assert "model_version" in body
    assert "model_backend" in body
    assert body["mqtt_enabled"] is False


def test_model_info(client: TestClient) -> None:
    response = client.get("/model/info")

    assert response.status_code == 200

    body = response.json()

    assert "model_name" in body
    assert "model_version" in body
    assert "model_backend" in body
    assert "anomaly_threshold" in body
    assert "model_manifest" in body


def test_infer_valid_request(client: TestClient) -> None:
    response = client.post(
        "/infer",
        json={
            "device_id": "device-001",
            "device_type": "vibration_sensor",
            "payload_type": "vibration",
            "features": [0.1, 0.2, 0.3],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["device_id"] == "device-001"
    assert body["device_type"] == "vibration_sensor"
    assert body["prediction"] in {"normal", "anomaly"}
    assert isinstance(body["anomaly_score"], float)
    assert isinstance(body["confidence"], float)


def test_infer_rejects_empty_features(client: TestClient) -> None:
    response = client.post(
        "/infer",
        json={
            "device_id": "device-001",
            "features": [],
        },
    )

    assert response.status_code == 422


def test_metrics(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "edgepulse_" in response.text
