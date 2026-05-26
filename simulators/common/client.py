from __future__ import annotations

import json

import paho.mqtt.publish as mqtt_publish
import requests


def post_inference(endpoint: str, payload: dict, timeout_seconds: int = 5) -> dict:
    response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def publish_mqtt(host: str, port: int, topic: str, payload: dict) -> None:
    mqtt_publish.single(
        topic=topic,
        payload=json.dumps(payload),
        qos=0,
        retain=False,
        hostname=host,
        port=port,
        client_id="edgepulse-simulator",
    )
