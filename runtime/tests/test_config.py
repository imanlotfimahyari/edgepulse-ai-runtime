import pytest
from app.config import Settings
from pydantic import ValidationError


def test_default_settings():
    settings = Settings()

    assert settings.model_backend == "rule-based"
    assert settings.anomaly_threshold == 0.65
    assert settings.mqtt_port == 1883


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
