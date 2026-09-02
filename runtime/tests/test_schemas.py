from __future__ import annotations

from datetime import datetime

import pytest
from app.schemas import InferenceRequest
from pydantic import ValidationError


def test_valid_inference_request() -> None:
    request = InferenceRequest(
        device_id="device-001",
        device_type="vibration_sensor",
        payload_type="vibration",
        features=[0.1, 0.2, 0.3],
        timestamp="2026-09-02T08:00:00Z",
    )

    assert request.device_id == "device-001"
    assert request.device_type == "vibration_sensor"
    assert request.features == [0.1, 0.2, 0.3]
    assert isinstance(request.timestamp, datetime)


def test_empty_features_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InferenceRequest(
            device_id="device-001",
            features=[],
        )


def test_missing_features_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InferenceRequest(
            device_id="device-001",
        )


def test_non_numeric_features_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InferenceRequest(
            device_id="device-001",
            features=["invalid"],
        )


def test_invalid_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InferenceRequest(
            device_id="device-001",
            features=[0.1],
            timestamp="not-a-timestamp",
        )
