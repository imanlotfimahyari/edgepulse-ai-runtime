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
    assert "execution_profile" in body
    assert body["execution_profile"]["name"] == settings.execution_profile
    assert "active" in body["execution_profile"]
    assert "model_path" in body
    assert "model_manifest_path" in body

    assert body["model_path"] == settings.model_path

    assert body["model_manifest_path"] == settings.model_manifest_path


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
    assert "edgepulse_model_runtime_info" in response.text


def test_readyz_reports_not_ready_when_initialization_fails(monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main.settings, "model_backend", "onnx")
    monkeypatch.setattr(main.settings, "mqtt_enabled", False)

    def fail_to_load_model():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(
        main.inference,
        "_get_onnx_session",
        fail_to_load_model,
    )

    with TestClient(main.app) as test_client:
        response = test_client.get("/readyz")

    assert response.status_code == 503

    body = response.json()

    assert body["status"] == "not-ready"
    assert body["model_backend"] == "onnx"
    assert body["error"] == "model unavailable"


def test_readyz_reports_not_ready_when_mqtt_disconnected(monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main.settings, "mqtt_enabled", True)
    monkeypatch.setattr(main, "start_mqtt_consumer", lambda: None)
    monkeypatch.setattr(main, "is_mqtt_connected", lambda: False)

    with TestClient(main.app) as test_client:
        response = test_client.get("/readyz")

    assert response.status_code == 503

    body = response.json()

    assert body["status"] == "not-ready"
    assert body["mqtt_enabled"] is True
    assert body["error"] == "mqtt broker not connected"


def test_readyz_is_ready_when_mqtt_connected(monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main.settings, "mqtt_enabled", True)
    monkeypatch.setattr(main, "start_mqtt_consumer", lambda: None)
    monkeypatch.setattr(main, "is_mqtt_connected", lambda: True)

    with TestClient(main.app) as test_client:
        response = test_client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_model_info_reports_active_onnx_profile(
    monkeypatch,
) -> None:
    from app import main

    monkeypatch.setattr(
        main.settings,
        "model_backend",
        "onnx",
    )
    monkeypatch.setattr(
        main.settings,
        "execution_profile",
        "eco",
    )
    monkeypatch.setattr(
        main.inference,
        "_get_onnx_session",
        lambda: object(),
    )
    monkeypatch.setattr(
        main.settings,
        "mqtt_enabled",
        False,
    )

    with TestClient(main.app) as test_client:
        response = test_client.get("/model/info")

    assert response.status_code == 200

    profile = response.json()["execution_profile"]

    assert profile["name"] == "eco"
    assert profile["active"] is True
    assert profile["intra_op_num_threads"] == 1
    assert profile["execution_mode"] == "sequential"
    assert profile["allow_spinning"] is False


def test_model_info_reports_profile_inactive_for_rule_backend(
    monkeypatch,
) -> None:
    from app import main

    monkeypatch.setattr(
        main.settings,
        "model_backend",
        "rule-based",
    )
    monkeypatch.setattr(
        main.settings,
        "execution_profile",
        "eco",
    )
    monkeypatch.setattr(
        main.settings,
        "mqtt_enabled",
        False,
    )

    with TestClient(main.app) as test_client:
        response = test_client.get("/model/info")

    profile = response.json()["execution_profile"]

    assert profile["name"] == "eco"
    assert profile["active"] is False
