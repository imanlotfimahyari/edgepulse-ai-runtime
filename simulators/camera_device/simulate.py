from __future__ import annotations

import random
from uuid import uuid4

from simulators.common.payloads import (
    is_anomaly_event,
    normalized_feature_vector,
    utc_timestamp,
)
from simulators.common.runner import run_simulator


def build_payload(device_id: str, anomaly_rate: float) -> dict:
    anomaly = is_anomaly_event(anomaly_rate)
    frame_id = f"frame-{uuid4().hex[:8]}"

    return {
        "device_id": device_id,
        "device_type": "camera_device",
        "payload_type": "preprocessed_frame_features",
        "features": normalized_feature_vector(anomaly=anomaly, size=10),
        "timestamp": utc_timestamp(),
        "metadata": {
            "generated_anomaly": anomaly,
            "frame_id": frame_id,
            "detected_objects": random.randint(0, 6),
            "source": "simulated_camera_feature_extractor",
        },
    }


if __name__ == "__main__":
    run_simulator(
        description="Simulated camera-like edge device.",
        default_device_id="device-camera-001",
        default_mqtt_topic="edge/devices/camera/telemetry",
        build_payload=build_payload,
    )
