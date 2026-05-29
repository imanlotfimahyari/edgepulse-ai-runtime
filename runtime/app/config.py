import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "edgepulse-ai-runtime")
    model_name: str = os.getenv("MODEL_NAME", "edgepulse-anomaly-detector")
    model_version: str = os.getenv("MODEL_VERSION", "0.9.0")
    model_backend: str = os.getenv("MODEL_BACKEND", "rule-based")
    model_path: str = os.getenv("MODEL_PATH", "/app/models/anomaly_score.onnx")
    anomaly_threshold: float = float(os.getenv("ANOMALY_THRESHOLD", "0.65"))

    mqtt_enabled: bool = env_bool("MQTT_ENABLED", False)
    mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "edge/devices/+/telemetry")


settings = Settings()
