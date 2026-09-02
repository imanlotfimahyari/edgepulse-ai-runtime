from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "edgepulse-ai-runtime"

    model_name: str = "edgepulse-anomaly-detector"
    model_version: str = "0.9.0"
    model_backend: Literal["rule-based", "onnx"] = "rule-based"
    model_path: str = "/app/models/anomaly_score.onnx"
    anomaly_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

    mqtt_enabled: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_topic: str = "edge/devices/+/telemetry"


settings = Settings()
