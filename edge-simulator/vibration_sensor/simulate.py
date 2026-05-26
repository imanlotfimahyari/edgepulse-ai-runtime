from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

import requests


def generate_features(anomaly_rate: float) -> tuple[list[float], bool]:
    is_anomaly = random.random() < anomaly_rate

    if is_anomaly:
        return [round(random.uniform(0.75, 1.20), 4) for _ in range(8)], True

    return [round(random.uniform(0.05, 0.45), 4) for _ in range(8)], False


def build_payload(device_id: str, anomaly_rate: float) -> dict:
    features, generated_anomaly = generate_features(anomaly_rate)

    return {
        "device_id": device_id,
        "device_type": "vibration_sensor",
        "payload_type": "vibration",
        "features": features,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "generated_anomaly": generated_anomaly,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated vibration edge device.")
    parser.add_argument("--endpoint", default="http://localhost:8080/infer")
    parser.add_argument("--device-id", default="device-vibration-001")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--anomaly-rate", type=float, default=0.05)

    args = parser.parse_args()

    for index in range(args.count):
        payload = build_payload(args.device_id, args.anomaly_rate)

        response = requests.post(args.endpoint, json=payload, timeout=5)
        response.raise_for_status()

        result = response.json()
        print(
            f"[{index + 1}/{args.count}] "
            f"device={result['device_id']} "
            f"prediction={result['prediction']} "
            f"score={result['anomaly_score']} "
            f"latency_ms={result['latency_ms']}"
        )

        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
