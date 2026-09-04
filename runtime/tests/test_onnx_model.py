from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import pytest
from onnx import TensorProto

from scripts.create_onnx_model import (
    create_model,
)
from scripts.quantize_onnx_model import (
    quantize_model,
)


def test_quantized_model_contains_int8_weights(
    tmp_path: Path,
) -> None:
    fp32_path = tmp_path / "fp32.onnx"

    int8_path = tmp_path / "int8.onnx"

    create_model(fp32_path)

    quantize_model(
        fp32_path,
        int8_path,
    )

    model = onnx.load(int8_path)

    quantized_initializers = [
        initializer
        for initializer in model.graph.initializer
        if initializer.data_type
        in {
            TensorProto.INT8,
            TensorProto.UINT8,
        }
    ]

    assert quantized_initializers


def test_quantized_model_is_smaller(
    tmp_path: Path,
) -> None:
    fp32_path = tmp_path / "fp32.onnx"

    int8_path = tmp_path / "int8.onnx"

    create_model(fp32_path)

    quantize_model(
        fp32_path,
        int8_path,
    )

    assert int8_path.stat().st_size < fp32_path.stat().st_size


@pytest.mark.parametrize(
    "features",
    [
        [0.1],
        [0.1, 0.2, 0.3],
        [
            0.12,
            0.14,
            0.19,
            0.25,
            0.22,
        ],
        [
            -0.5,
            0.25,
            1.25,
            -1.0,
        ],
        [0.8, 0.9, 1.0],
    ],
)
def test_quantized_model_remains_close_to_fp32(
    tmp_path: Path,
    features: list[float],
) -> None:
    fp32_path = tmp_path / "fp32.onnx"

    int8_path = tmp_path / "int8.onnx"

    create_model(fp32_path)

    quantize_model(
        fp32_path,
        int8_path,
    )

    fp32_score = _run_model(
        fp32_path,
        features,
    )

    int8_score = _run_model(
        int8_path,
        features,
    )

    assert int8_score == pytest.approx(
        fp32_score,
        rel=0.03,
        abs=0.01,
    )


def _run_model(
    model_path: Path,
    features: list[float],
) -> float:
    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )

    output = session.run(
        None,
        {
            "features": np.asarray(
                features,
                dtype=np.float32,
            )
        },
    )

    return float(np.asarray(output[0]).reshape(()))


def test_generated_model_contains_quantizable_weights(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "anomaly_score.onnx"

    create_model(model_path)

    model = onnx.load(model_path)

    node_types = [node.op_type for node in model.graph.node]

    assert node_types.count("MatMul") == 3

    assert node_types.count("Relu") == 2

    initializer_names = {initializer.name for initializer in model.graph.initializer}

    assert {
        "weight_1",
        "weight_2",
        "weight_3",
        "bias_1",
        "bias_2",
        "bias_3",
    }.issubset(initializer_names)

    assert model_path.stat().st_size > 100_000


@pytest.mark.parametrize(
    "features",
    [
        [0.1],
        [0.1, 0.2, 0.3],
        [
            0.12,
            0.14,
            0.19,
            0.25,
            0.22,
        ],
        [
            -0.5,
            0.25,
            1.25,
            -1.0,
            0.0,
        ],
        [0.8, 0.9, 1.0],
    ],
)
def test_generated_model_preserves_mean_absolute_score(
    tmp_path: Path,
    features: list[float],
) -> None:
    model_path = tmp_path / "anomaly_score.onnx"

    create_model(model_path)

    actual = _run_model(
        model_path,
        features,
    )

    expected = float(
        np.mean(
            np.abs(
                np.asarray(
                    features,
                    dtype=np.float32,
                )
            )
        )
    )

    assert actual == pytest.approx(
        expected,
        rel=1e-5,
        abs=1e-6,
    )


def test_generated_model_is_deterministic(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.onnx"

    second = tmp_path / "second.onnx"

    create_model(first)
    create_model(second)

    assert first.read_bytes() == second.read_bytes()
