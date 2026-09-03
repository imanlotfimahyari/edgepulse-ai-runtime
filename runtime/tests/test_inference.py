from __future__ import annotations

import numpy as np
import onnxruntime as ort
from app import inference
from app.execution_profiles import get_execution_profile


def test_rule_based_backend_returns_normal(monkeypatch) -> None:
    monkeypatch.setattr(inference.settings, "model_backend", "rule-based")
    monkeypatch.setattr(inference.settings, "anomaly_threshold", 0.65)

    prediction, anomaly_score, confidence = inference.run_inference([0.1, 0.2, 0.3])

    assert prediction == "normal"
    assert anomaly_score == 0.2
    assert confidence == 0.8


def test_rule_based_backend_returns_anomaly(monkeypatch) -> None:
    monkeypatch.setattr(inference.settings, "model_backend", "rule-based")
    monkeypatch.setattr(inference.settings, "anomaly_threshold", 0.65)

    prediction, anomaly_score, confidence = inference.run_inference([0.8, 0.9, 1.0])

    assert prediction == "anomaly"
    assert anomaly_score == 0.9
    assert confidence == 0.9


def test_score_equal_to_threshold_is_anomaly(monkeypatch) -> None:
    monkeypatch.setattr(inference.settings, "model_backend", "rule-based")
    monkeypatch.setattr(inference.settings, "anomaly_threshold", 0.65)

    prediction, anomaly_score, confidence = inference.run_inference([0.65])

    assert prediction == "anomaly"
    assert anomaly_score == 0.65
    assert confidence == 0.65


def test_rule_based_empty_features_returns_anomaly(monkeypatch) -> None:
    monkeypatch.setattr(inference.settings, "model_backend", "rule-based")
    monkeypatch.setattr(inference.settings, "anomaly_threshold", 0.65)

    prediction, anomaly_score, confidence = inference._run_rule_based_inference([])

    assert prediction == "anomaly"
    assert anomaly_score == 1.0
    assert confidence == 1.0


def test_onnx_backend_uses_session(monkeypatch) -> None:
    class FakeSession:
        def run(
            self,
            output_names: object,
            inputs: dict[str, np.ndarray],
        ) -> list[np.ndarray]:
            assert output_names is None
            assert "features" in inputs
            assert inputs["features"].dtype == np.float32

            return [np.asarray(0.75, dtype=np.float32)]

    monkeypatch.setattr(inference.settings, "model_backend", "onnx")
    monkeypatch.setattr(inference.settings, "anomaly_threshold", 0.65)
    monkeypatch.setattr(
        inference,
        "_get_onnx_session",
        lambda: FakeSession(),
    )

    prediction, anomaly_score, confidence = inference.run_inference([0.1, 0.2, 0.3])

    assert prediction == "anomaly"
    assert anomaly_score == 0.75
    assert confidence == 0.75


def test_eco_profile_builds_single_threaded_session_options() -> None:
    profile = get_execution_profile("eco")

    options = inference._build_onnx_session_options(
        profile,
    )

    assert options.intra_op_num_threads == 1
    assert options.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL

    assert options.get_session_config_entry("session.intra_op.allow_spinning") == "0"


def test_balanced_profile_builds_default_thread_session_options() -> None:
    profile = get_execution_profile("balanced")

    options = inference._build_onnx_session_options(
        profile,
    )

    assert options.intra_op_num_threads == 0
    assert options.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL

    assert options.get_session_config_entry("session.intra_op.allow_spinning") == "1"
