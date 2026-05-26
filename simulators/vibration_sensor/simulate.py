from __future__ import annotations

from simulators.common.payloads import (
    is_anomaly_event,
    normalized_feature_vector,
    utc_timestamp,
)
from simulators.common.runner import run_simulator


def build_payload(device_id: str, anomaly_rate: float) -> dict:
    anomaly = is_anomaly_event(anomaly_rate)

    return {
        "device_id": device_id,
        "device_type": "vibration_sensor",
        "payload_type": "vibration",
        "features": normalized_feature_vector(anomaly=anomaly, size=8),
        "timestamp": utc_timestamp(),
        "metadata": {
            "generated_anomaly": anomaly,
            "unit": "normalized_vibration",
            "source": "simulated_motor_sensor",
        },
    }


if __name__ == "__main__":
    run_simulator(
        description="Simulated vibration edge device.",
        default_device_id="device-vibration-001",
        default_mqtt_topic="edge/devices/vibration/telemetry",
        build_payload=build_payload,
    )
