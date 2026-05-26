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
        voltage = round(random.uniform(245.0, 265.0), 2)
        current = round(random.uniform(12.0, 24.0), 2)
    else:
        voltage = round(random.uniform(220.0, 235.0), 2)
        current = round(random.uniform(1.0, 5.0), 2)

    power_w = round(voltage * current, 2)

    return {
        "device_id": device_id,
        "device_type": "power_meter",
        "payload_type": "power",
        "features": normalized_feature_vector(anomaly=anomaly, size=6),
        "timestamp": utc_timestamp(),
        "metadata": {
            "generated_anomaly": anomaly,
            "voltage": voltage,
            "current": current,
            "power_w": power_w,
            "source": "simulated_power_meter",
        },
    }


if __name__ == "__main__":
    run_simulator(
        description="Simulated power meter edge device.",
        default_device_id="device-power-001",
        default_mqtt_topic="edge/devices/power/telemetry",
        build_payload=build_payload,
    )
