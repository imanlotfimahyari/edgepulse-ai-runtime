from __future__ import annotations

import random

from simulators.common.payloads import (
    is_anomaly_event,
    normalized_feature_vector,
    utc_timestamp,
)
from simulators.common.runner import run_simulator


def build_payload(device_id: str, anomaly_rate: float) -> dict:
    anomaly = is_anomaly_event(anomaly_rate)

    if anomaly:
        temperature_c = round(random.uniform(55.0, 85.0), 2)
        humidity_percent = round(random.uniform(10.0, 25.0), 2)
    else:
        temperature_c = round(random.uniform(18.0, 32.0), 2)
        humidity_percent = round(random.uniform(35.0, 60.0), 2)

    return {
        "device_id": device_id,
        "device_type": "temperature_sensor",
        "payload_type": "environmental",
        "features": normalized_feature_vector(anomaly=anomaly, size=6),
        "timestamp": utc_timestamp(),
        "metadata": {
            "generated_anomaly": anomaly,
            "temperature_c": temperature_c,
            "humidity_percent": humidity_percent,
            "source": "simulated_environmental_sensor",
        },
    }


if __name__ == "__main__":
    run_simulator(
        description="Simulated temperature edge device.",
        default_device_id="device-temp-001",
        default_mqtt_topic="edge/devices/temperature/telemetry",
        build_payload=build_payload,
    )
