from __future__ import annotations

import argparse
import time
from collections.abc import Callable

from simulators.common.client import post_inference, publish_mqtt


def run_simulator(
    description: str,
    default_device_id: str,
    default_mqtt_topic: str,
    build_payload: Callable[[str, float], dict],
) -> None:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--mode", choices=["http", "mqtt"], default="http")
    parser.add_argument("--endpoint", default="http://localhost:8080/infer")
    parser.add_argument("--device-id", default=default_device_id)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--anomaly-rate", type=float, default=0.05)

    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-topic", default=default_mqtt_topic)

    args = parser.parse_args()

    for index in range(args.count):
        payload = build_payload(args.device_id, args.anomaly_rate)

        if args.mode == "http":
            result = post_inference(args.endpoint, payload)

            print(
                f"[{index + 1}/{args.count}] "
                f"mode=http "
                f"device={result['device_id']} "
                f"type={result['device_type']} "
                f"prediction={result['prediction']} "
                f"score={result['anomaly_score']} "
                f"latency_ms={result['latency_ms']}"
            )

        else:
            publish_mqtt(args.mqtt_host, args.mqtt_port, args.mqtt_topic, payload)

            print(
                f"[{index + 1}/{args.count}] "
                f"mode=mqtt "
                f"device={payload['device_id']} "
                f"type={payload['device_type']} "
                f"topic={args.mqtt_topic} "
                f"generated_anomaly={payload.get('metadata', {}).get('generated_anomaly')}"
            )

        time.sleep(args.interval_seconds)
