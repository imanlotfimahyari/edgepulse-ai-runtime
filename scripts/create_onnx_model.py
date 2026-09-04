from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

DEFAULT_MODEL_PATH = Path("runtime/models/anomaly_score.onnx")

RANDOM_SEED = 20260903

HIDDEN_LAYER_1 = 256
HIDDEN_LAYER_2 = 128


def _build_weights() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(RANDOM_SEED)

    weight_1 = rng.uniform(
        0.5,
        1.5,
        size=(1, HIDDEN_LAYER_1),
    ).astype(np.float32)

    weight_2 = rng.uniform(
        0.5,
        1.5,
        size=(
            HIDDEN_LAYER_1,
            HIDDEN_LAYER_2,
        ),
    ).astype(np.float32)

    weight_3 = rng.uniform(
        0.5,
        1.5,
        size=(HIDDEN_LAYER_2, 1),
    ).astype(np.float32)

    #
    # All weights are positive and the input to
    # the network is mean(abs(features)), so ReLU
    # does not alter the signal.
    #
    # Normalize the final layer so that the entire
    # network has approximately unit gain:
    #
    #     output ~= mean(abs(features))
    #
    gain = float((weight_1 @ weight_2 @ weight_3).reshape(()))

    weight_3 = (weight_3 / gain).astype(np.float32)

    return {
        "weight_1": weight_1,
        "bias_1": np.zeros(
            HIDDEN_LAYER_1,
            dtype=np.float32,
        ),
        "weight_2": weight_2,
        "bias_2": np.zeros(
            HIDDEN_LAYER_2,
            dtype=np.float32,
        ),
        "weight_3": weight_3,
        "bias_3": np.zeros(
            1,
            dtype=np.float32,
        ),
    }


def build_model() -> onnx.ModelProto:
    input_tensor = helper.make_tensor_value_info(
        "features",
        TensorProto.FLOAT,
        ["num_features"],
    )

    output_tensor = helper.make_tensor_value_info(
        "anomaly_score",
        TensorProto.FLOAT,
        [1],
    )

    weights = _build_weights()

    initializers = [
        numpy_helper.from_array(
            np.asarray(
                [1],
                dtype=np.int64,
            ),
            name="summary_shape",
        ),
        numpy_helper.from_array(
            weights["weight_1"],
            name="weight_1",
        ),
        numpy_helper.from_array(
            weights["bias_1"],
            name="bias_1",
        ),
        numpy_helper.from_array(
            weights["weight_2"],
            name="weight_2",
        ),
        numpy_helper.from_array(
            weights["bias_2"],
            name="bias_2",
        ),
        numpy_helper.from_array(
            weights["weight_3"],
            name="weight_3",
        ),
        numpy_helper.from_array(
            weights["bias_3"],
            name="bias_3",
        ),
    ]

    nodes = [
        helper.make_node(
            "Abs",
            inputs=["features"],
            outputs=["abs_features"],
            name="absolute_feature_values",
        ),
        helper.make_node(
            "ReduceMean",
            inputs=["abs_features"],
            outputs=["mean_absolute_feature"],
            name="mean_absolute_feature_value",
            keepdims=0,
        ),
        helper.make_node(
            "Reshape",
            inputs=[
                "mean_absolute_feature",
                "summary_shape",
            ],
            outputs=["summary_vector"],
            name="reshape_feature_summary",
        ),
        helper.make_node(
            "MatMul",
            inputs=[
                "summary_vector",
                "weight_1",
            ],
            outputs=["hidden_1_linear"],
            name="hidden_1_matmul",
        ),
        helper.make_node(
            "Add",
            inputs=[
                "hidden_1_linear",
                "bias_1",
            ],
            outputs=["hidden_1_biased"],
            name="hidden_1_bias",
        ),
        helper.make_node(
            "Relu",
            inputs=["hidden_1_biased"],
            outputs=["hidden_1"],
            name="hidden_1_relu",
        ),
        helper.make_node(
            "MatMul",
            inputs=[
                "hidden_1",
                "weight_2",
            ],
            outputs=["hidden_2_linear"],
            name="hidden_2_matmul",
        ),
        helper.make_node(
            "Add",
            inputs=[
                "hidden_2_linear",
                "bias_2",
            ],
            outputs=["hidden_2_biased"],
            name="hidden_2_bias",
        ),
        helper.make_node(
            "Relu",
            inputs=["hidden_2_biased"],
            outputs=["hidden_2"],
            name="hidden_2_relu",
        ),
        helper.make_node(
            "MatMul",
            inputs=[
                "hidden_2",
                "weight_3",
            ],
            outputs=["score_linear"],
            name="output_matmul",
        ),
        helper.make_node(
            "Add",
            inputs=[
                "score_linear",
                "bias_3",
            ],
            outputs=["anomaly_score"],
            name="output_bias",
        ),
    ]

    graph = helper.make_graph(
        nodes=nodes,
        name=("edgepulse_weighted_anomaly_score_model"),
        inputs=[input_tensor],
        outputs=[output_tensor],
        initializer=initializers,
    )

    model = helper.make_model(
        graph,
        producer_name=("edgepulse-ai-runtime"),
        producer_version="0.9.0",
        opset_imports=[
            helper.make_opsetid(
                "",
                13,
            )
        ],
        ir_version=10,
    )

    model.doc_string = (
        "Deterministic weight-bearing "
        "EdgePulse anomaly scoring model "
        "for runtime optimization and "
        "quantization experiments."
    )

    onnx.checker.check_model(model)

    return model


def create_model(
    model_path: Path = DEFAULT_MODEL_PATH,
) -> Path:
    model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model = build_model()

    onnx.save(
        model,
        model_path,
    )

    return model_path


def main() -> None:
    model_path = create_model()

    print(f"Created {model_path}")

    print(f"Artifact size: {model_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
