from __future__ import annotations

from types import SimpleNamespace

from app import mqtt_consumer
from pydantic import SecretStr


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


def test_on_connect_marks_mqtt_connected(monkeypatch) -> None:
    class FakeMetric:
        def __init__(self) -> None:
            self.value = None

        def set(self, value) -> None:
            self.value = value

    class FakeClient:
        def __init__(self) -> None:
            self.topic = None

        def subscribe(self, topic):
            self.topic = topic

    fake_metric = FakeMetric()
    fake_client = FakeClient()

    monkeypatch.setattr(
        mqtt_consumer,
        "MQTT_CONNECTED",
        fake_metric,
    )

    mqtt_consumer._mqtt_connected.clear()

    mqtt_consumer._on_connect(
        fake_client,
        None,
        None,
        0,
        None,
    )

    assert mqtt_consumer.is_mqtt_connected() is True
    assert fake_metric.value == 1
    assert fake_client.topic == mqtt_consumer.settings.mqtt_topic


def test_on_connect_failure_marks_mqtt_disconnected(monkeypatch) -> None:
    class FakeMetric:
        def __init__(self) -> None:
            self.value = None

        def set(self, value) -> None:
            self.value = value

    class FakeClient:
        def subscribe(self, topic):
            raise AssertionError("subscribe must not be called")

    fake_metric = FakeMetric()

    monkeypatch.setattr(
        mqtt_consumer,
        "MQTT_CONNECTED",
        fake_metric,
    )

    mqtt_consumer._mqtt_connected.set()

    mqtt_consumer._on_connect(
        FakeClient(),
        None,
        None,
        1,
        None,
    )

    assert mqtt_consumer.is_mqtt_connected() is False
    assert fake_metric.value == 0


def test_on_disconnect_marks_mqtt_disconnected(monkeypatch) -> None:
    class FakeMetric:
        def __init__(self) -> None:
            self.value = None

        def set(self, value) -> None:
            self.value = value

    fake_metric = FakeMetric()

    monkeypatch.setattr(
        mqtt_consumer,
        "MQTT_CONNECTED",
        fake_metric,
    )

    mqtt_consumer._mqtt_connected.set()

    mqtt_consumer._on_disconnect(
        None,
        None,
        None,
        1,
        None,
    )

    assert mqtt_consumer.is_mqtt_connected() is False
    assert fake_metric.value == 0


def test_mqtt_consumer_configures_async_reconnect(monkeypatch) -> None:
    calls = {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.on_connect = None
            self.on_connect_fail = None
            self.on_disconnect = None
            self.on_message = None

        def reconnect_delay_set(self, min_delay, max_delay) -> None:
            calls["reconnect_delay"] = (min_delay, max_delay)

        def connect_async(self, host, port, keepalive) -> None:
            calls["connect_async"] = (host, port, keepalive)

        def loop_forever(self, retry_first_connection=False) -> None:
            calls["retry_first_connection"] = retry_first_connection

    monkeypatch.setattr(
        mqtt_consumer.mqtt,
        "Client",
        FakeClient,
    )

    mqtt_consumer._run_mqtt_consumer()

    assert calls["reconnect_delay"] == (1, 30)
    assert calls["connect_async"] == (
        mqtt_consumer.settings.mqtt_host,
        mqtt_consumer.settings.mqtt_port,
        60,
    )
    assert calls["retry_first_connection"] is True


def test_configure_mqtt_username_password(monkeypatch) -> None:
    calls = {}

    class FakeClient:
        def username_pw_set(self, username, password=None) -> None:
            calls["auth"] = (username, password)

    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_username",
        "edgepulse-runtime",
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_password",
        SecretStr("test-password"),
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_tls_enabled",
        False,
    )

    mqtt_consumer._configure_mqtt_security(FakeClient())

    assert calls["auth"] == (
        "edgepulse-runtime",
        "test-password",
    )


def test_configure_mqtt_tls(monkeypatch) -> None:
    calls = {}

    class FakeClient:
        def tls_set(
            self,
            ca_certs=None,
            certfile=None,
            keyfile=None,
        ) -> None:
            calls["tls"] = (
                ca_certs,
                certfile,
                keyfile,
            )

    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_username",
        None,
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_password",
        None,
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_tls_enabled",
        True,
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_tls_ca_file",
        "/certs/ca.crt",
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_tls_cert_file",
        "/certs/client.crt",
    )
    monkeypatch.setattr(
        mqtt_consumer.settings,
        "mqtt_tls_key_file",
        "/certs/client.key",
    )

    mqtt_consumer._configure_mqtt_security(FakeClient())

    assert calls["tls"] == (
        "/certs/ca.crt",
        "/certs/client.crt",
        "/certs/client.key",
    )
