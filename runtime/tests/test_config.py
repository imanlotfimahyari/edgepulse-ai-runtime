import pytest
from app.config import Settings
from pydantic import ValidationError


def test_default_settings():
    settings = Settings()

    assert settings.model_backend == "rule-based"
    assert settings.anomaly_threshold == 0.65
    assert settings.mqtt_port == 1883
    assert settings.mqtt_username is None
    assert settings.mqtt_password is None
    assert settings.mqtt_tls_enabled is False


def test_valid_onnx_backend():
    settings = Settings(model_backend="onnx")

    assert settings.model_backend == "onnx"


def test_invalid_model_backend_is_rejected():
    with pytest.raises(ValidationError):
        Settings(model_backend="invalid")


def test_threshold_below_zero_is_rejected():
    with pytest.raises(ValidationError):
        Settings(anomaly_threshold=-0.1)


def test_threshold_above_one_is_rejected():
    with pytest.raises(ValidationError):
        Settings(anomaly_threshold=1.1)


def test_invalid_mqtt_port_is_rejected():
    with pytest.raises(ValidationError):
        Settings(mqtt_port=70000)


def test_mqtt_password_requires_username():
    with pytest.raises(
        ValidationError,
        match="mqtt_username is required",
    ):
        Settings(mqtt_password="secret")


def test_mqtt_client_certificate_requires_key():
    with pytest.raises(
        ValidationError,
        match="must be configured together",
    ):
        Settings(
            mqtt_tls_enabled=True,
            mqtt_tls_cert_file="/certs/client.crt",
        )


def test_mqtt_client_key_requires_certificate():
    with pytest.raises(
        ValidationError,
        match="must be configured together",
    ):
        Settings(
            mqtt_tls_enabled=True,
            mqtt_tls_key_file="/certs/client.key",
        )


def test_mqtt_tls_files_require_tls_enabled():
    with pytest.raises(
        ValidationError,
        match="mqtt_tls_enabled must be true",
    ):
        Settings(
            mqtt_tls_ca_file="/certs/ca.crt",
        )
