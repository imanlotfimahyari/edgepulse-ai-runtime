from __future__ import annotations

from functools import lru_cache

import numpy as np
import onnxruntime as ort
from app.config import settings
from app.execution_profiles import (
    ExecutionProfile,
    get_execution_profile,
)


def run_inference(features: list[float]) -> tuple[str, float, float]:
    if settings.model_backend == "onnx":
        return _run_onnx_inference(features)

    return _run_rule_based_inference(features)


def _run_rule_based_inference(features: list[float]) -> tuple[str, float, float]:
    if not features:
        anomaly_score = 1.0
    else:
        anomaly_score = sum(abs(value) for value in features) / len(features)

    return _prediction_from_score(anomaly_score)


def _run_onnx_inference(features: list[float]) -> tuple[str, float, float]:
    if not features:
        anomaly_score = 1.0
        return _prediction_from_score(anomaly_score)

    input_array = np.asarray(features, dtype=np.float32)

    session = _get_onnx_session()
    output = session.run(None, {"features": input_array})

    anomaly_score = float(np.asarray(output[0]).reshape(()))

    return _prediction_from_score(anomaly_score)


def _prediction_from_score(anomaly_score: float) -> tuple[str, float, float]:
    prediction = "anomaly" if anomaly_score >= settings.anomaly_threshold else "normal"

    if prediction == "anomaly":
        confidence = min(1.0, anomaly_score)
    else:
        confidence = min(1.0, 1.0 - anomaly_score)

    return prediction, round(anomaly_score, 4), round(confidence, 4)


def _build_onnx_session_options(
    profile: ExecutionProfile,
) -> ort.SessionOptions:
    options = ort.SessionOptions()

    options.intra_op_num_threads = profile.intra_op_num_threads
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    spinning = "1" if profile.allow_spinning else "0"

    options.add_session_config_entry(
        "session.intra_op.allow_spinning",
        spinning,
    )

    return options


@lru_cache(maxsize=1)
def _get_onnx_session() -> ort.InferenceSession:
    profile = get_execution_profile(
        settings.execution_profile,
    )

    session_options = _build_onnx_session_options(
        profile,
    )

    return ort.InferenceSession(
        settings.model_path,
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )
