from __future__ import annotations

from types import SimpleNamespace

from app import mqtt_consumer


def test_valid_mqtt_message_is_processed(monkeypatch) -> None:
    processed = {}

    def fake_process(request, ingestion):
        processed["request"] = request
        processed["ingestion"] = ingestion

        return SimpleNamespace(
            device_id=request.device_id,
            device_type=request.device_type,
            prediction="normal",
            anomaly_score=0.2,
            latency_ms=1.0,
        )

    monkeypatch.setattr(
        mqtt_consumer,
        "process_inference_request",
        fake_process,
    )

    message = SimpleNamespace(
        topic="edge/devices/device-001/telemetry",
        payload=(
            b'{"device_id":"device-001",'
            b'"device_type":"vibration_sensor",'
            b'"features":[0.1,0.2,0.3]}'
        ),
    )

    mqtt_consumer._on_message(
        client=None,
        userdata=None,
        message=message,
    )

    assert processed["request"].device_id == "device-001"
    assert processed["request"].device_type == "vibration_sensor"
    assert processed["ingestion"] == "mqtt"


def test_invalid_json_does_not_escape_callback(monkeypatch) -> None:
    class FakeMetric:
        def __init__(self) -> None:
            self.count = 0

        def labels(self, **kwargs):
            return self

        def inc(self) -> None:
            self.count += 1

    fake_errors = FakeMetric()

    monkeypatch.setattr(
        mqtt_consumer,
        "MQTT_ERRORS",
        fake_errors,
    )

    message = SimpleNamespace(
        topic="edge/devices/device-001/telemetry",
        payload=b"not-json",
    )

    mqtt_consumer._on_message(
        client=None,
        userdata=None,
        message=message,
    )

    assert fake_errors.count == 1


def test_schema_invalid_mqtt_message_counts_error(monkeypatch) -> None:
    class FakeMetric:
        def __init__(self) -> None:
            self.count = 0

        def labels(self, **kwargs):
            return self

        def inc(self) -> None:
            self.count += 1

    fake_errors = FakeMetric()

    monkeypatch.setattr(
        mqtt_consumer,
        "MQTT_ERRORS",
        fake_errors,
    )

    message = SimpleNamespace(
        topic="edge/devices/device-001/telemetry",
        payload=(b'{"device_id":"device-001","features":[]}'),
    )

    mqtt_consumer._on_message(
        client=None,
        userdata=None,
        message=message,
    )

    assert fake_errors.count == 1
