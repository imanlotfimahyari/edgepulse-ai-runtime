from __future__ import annotations

import argparse
import random
import time

from simulators.common.client import post_inference
from simulators.common.payloads import (
    is_anomaly_event,
    normalized_feature_vector,
    utc_timestamp,
)


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated temperature edge device.")
    parser.add_argument("--endpoint", default="http://localhost:8080/infer")
    parser.add_argument("--device-id", default="device-temp-001")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--anomaly-rate", type=float, default=0.05)

    args = parser.parse_args()

    for index in range(args.count):
        payload = build_payload(args.device_id, args.anomaly_rate)
        result = post_inference(args.endpoint, payload)

        print(
            f"[{index + 1}/{args.count}] "
            f"device={result['device_id']} "
            f"type={result['device_type']} "
            f"prediction={result['prediction']} "
            f"score={result['anomaly_score']} "
            f"latency_ms={result['latency_ms']}"
        )

        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
