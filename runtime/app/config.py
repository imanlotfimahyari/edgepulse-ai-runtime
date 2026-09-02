from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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

    mqtt_username: str | None = None
    mqtt_password: SecretStr | None = None

    mqtt_tls_enabled: bool = False
    mqtt_tls_ca_file: str | None = None
    mqtt_tls_cert_file: str | None = None
    mqtt_tls_key_file: str | None = None

    @model_validator(mode="after")
    def validate_mqtt_security(self) -> Self:
        if self.mqtt_password is not None and self.mqtt_username is None:
            raise ValueError("mqtt_username is required when mqtt_password is set")

        if (self.mqtt_tls_cert_file is None) != (self.mqtt_tls_key_file is None):
            raise ValueError(
                "mqtt_tls_cert_file and mqtt_tls_key_file must be configured together"
            )

        tls_files_configured = any(
            (
                self.mqtt_tls_ca_file,
                self.mqtt_tls_cert_file,
                self.mqtt_tls_key_file,
            )
        )

        if tls_files_configured and not self.mqtt_tls_enabled:
            raise ValueError(
                "mqtt_tls_enabled must be true when MQTT TLS files are configured"
            )

        return self


settings = Settings()
