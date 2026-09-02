from __future__ import annotations

import os
import time

import requests

from simulators.common.client import post_inference, publish_mqtt
from simulators.vibration_sensor.simulate import build_payload

BASE_URL = os.getenv(
    "EDGEPULSE_BASE_URL",
    "http://localhost:8080",
)

MQTT_HOST = os.getenv(
    "EDGEPULSE_MQTT_HOST",
    "localhost",
)

MQTT_PORT = int(
    os.getenv(
        "EDGEPULSE_MQTT_PORT",
        "1883",
    )
)

MQTT_USERNAME = os.getenv(
    "EDGEPULSE_MQTT_USERNAME",
)

MQTT_PASSWORD = os.getenv(
    "EDGEPULSE_MQTT_PASSWORD",
)

MQTT_TLS_CA_FILE = os.getenv(
    "EDGEPULSE_MQTT_TLS_CA_FILE",
)

READY_TIMEOUT_SECONDS = 30
MQTT_PROCESSING_TIMEOUT_SECONDS = 10


def wait_for_ready() -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        try:
            response = requests.get(
                f"{BASE_URL}/readyz",
                timeout=2,
            )

            if response.status_code == 200:
                return

        except requests.RequestException:
            pass

        time.sleep(1)

    raise RuntimeError("EdgePulse runtime did not become ready")


def get_metrics() -> str:
    response = requests.get(
        f"{BASE_URL}/metrics",
        timeout=5,
    )
    response.raise_for_status()
    return response.text


def metrics_contains(metric_name: str, *labels: str) -> bool:
    for line in get_metrics().splitlines():
        if not line.startswith(metric_name):
            continue

        if all(label in line for label in labels):
            return True

    return False


def wait_for_mqtt_processing() -> None:
    deadline = time.monotonic() + MQTT_PROCESSING_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if metrics_contains(
            "edgepulse_inference_requests_total",
            'device_type="vibration_sensor"',
            'ingestion="mqtt"',
        ):
            return

        time.sleep(0.5)

    raise RuntimeError("MQTT message was not processed in time")


def main() -> None:
    wait_for_ready()

    health = requests.get(
        f"{BASE_URL}/healthz",
        timeout=5,
    )
    health.raise_for_status()

    assert health.json()["status"] == "ok"

    ready = requests.get(
        f"{BASE_URL}/readyz",
        timeout=5,
    )
    ready.raise_for_status()

    assert ready.json()["status"] == "ready"
    assert ready.json()["mqtt_enabled"] is True

    assert "edgepulse_mqtt_connected 1.0" in get_metrics()

    payload = build_payload(
        device_id="e2e-http-device",
        anomaly_rate=0.0,
    )

    result = post_inference(
        f"{BASE_URL}/infer",
        payload,
    )

    assert result["device_id"] == "e2e-http-device"
    assert result["device_type"] == "vibration_sensor"
    assert result["prediction"] in {"normal", "anomaly"}

    assert metrics_contains(
        "edgepulse_inference_requests_total",
        'device_type="vibration_sensor"',
        'ingestion="http"',
    )

    mqtt_payload = build_payload(
        device_id="e2e-mqtt-device",
        anomaly_rate=0.0,
    )

    publish_mqtt(
        host=MQTT_HOST,
        port=MQTT_PORT,
        topic="edge/devices/vibration/telemetry",
        payload=mqtt_payload,
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        tls_ca_file=MQTT_TLS_CA_FILE,
    )

    wait_for_mqtt_processing()

    assert metrics_contains(
        "edgepulse_mqtt_messages_total",
        'device_type="vibration_sensor"',
    )

    print("EdgePulse Compose E2E test passed")


if __name__ == "__main__":
    main()
