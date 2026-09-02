from __future__ import annotations

import json
import logging
import threading

import paho.mqtt.client as mqtt
from app.config import settings
from app.metrics import MQTT_CONNECTED, MQTT_ERRORS, MQTT_MESSAGES
from app.schemas import InferenceRequest
from app.service import process_inference_request

logger = logging.getLogger("edgepulse.mqtt")

_mqtt_connected = threading.Event()


def is_mqtt_connected() -> bool:
    return _mqtt_connected.is_set()


def start_mqtt_consumer() -> None:
    thread = threading.Thread(target=_run_mqtt_consumer, daemon=True)
    thread.start()


def _run_mqtt_consumer() -> None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="edgepulse-runtime",
    )

    client.on_connect = _on_connect
    client.on_connect_fail = _on_connect_fail
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    logger.info(
        "Starting MQTT consumer host=%s port=%s topic=%s",
        settings.mqtt_host,
        settings.mqtt_port,
        settings.mqtt_topic,
    )

    client.reconnect_delay_set(
        min_delay=1,
        max_delay=30,
    )

    client.connect_async(
        settings.mqtt_host,
        settings.mqtt_port,
        keepalive=60,
    )

    client.loop_forever(
        retry_first_connection=True,
    )


def _on_connect(
    client: mqtt.Client,
    userdata: object,
    flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: mqtt.Properties | None,
) -> None:
    if reason_code != 0:
        _mqtt_connected.clear()
        MQTT_CONNECTED.set(0)

        logger.warning(
            "MQTT connection refused reason_code=%s",
            reason_code,
        )
        return

    _mqtt_connected.set()
    MQTT_CONNECTED.set(1)

    logger.info(
        "MQTT connected reason_code=%s",
        reason_code,
    )

    client.subscribe(settings.mqtt_topic)


def _on_connect_fail(
    client: mqtt.Client,
    userdata: object,
) -> None:
    _mqtt_connected.clear()
    MQTT_CONNECTED.set(0)

    logger.warning(
        "MQTT connection attempt failed host=%s port=%s",
        settings.mqtt_host,
        settings.mqtt_port,
    )


def _on_disconnect(
    client: mqtt.Client,
    userdata: object,
    disconnect_flags: mqtt.DisconnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: mqtt.Properties | None,
) -> None:
    _mqtt_connected.clear()
    MQTT_CONNECTED.set(0)

    logger.warning(
        "MQTT disconnected reason_code=%s",
        reason_code,
    )


def _on_message(
    client: mqtt.Client,
    userdata: object,
    message: mqtt.MQTTMessage,
) -> None:
    topic = message.topic

    try:
        payload = json.loads(message.payload.decode("utf-8"))
        request = InferenceRequest.model_validate(payload)

        MQTT_MESSAGES.labels(
            topic=topic,
            device_type=request.device_type,
        ).inc()

        result = process_inference_request(request, ingestion="mqtt")

        logger.info(
            "MQTT inference processed topic=%s device=%s type=%s prediction=%s score=%s latency_ms=%s",
            topic,
            result.device_id,
            result.device_type,
            result.prediction,
            result.anomaly_score,
            result.latency_ms,
        )

    except Exception:
        MQTT_ERRORS.labels(topic=topic).inc()
        logger.exception("Failed to process MQTT message topic=%s", topic)
