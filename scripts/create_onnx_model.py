from __future__ import annotations

from pathlib import Path

import onnx
from onnx import TensorProto, helper


def main() -> None:
    output_dir = Path("runtime/models")
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "anomaly_score.onnx"

    input_tensor = helper.make_tensor_value_info(
        "features",
        TensorProto.FLOAT,
        ["num_features"],
    )

    output_tensor = helper.make_tensor_value_info(
        "anomaly_score",
        TensorProto.FLOAT,
        [],
    )

    abs_node = helper.make_node(
        "Abs",
        inputs=["features"],
        outputs=["abs_features"],
        name="absolute_feature_values",
    )

    mean_node = helper.make_node(
        "ReduceMean",
        inputs=["abs_features"],
        outputs=["anomaly_score"],
        name="mean_absolute_feature_value",
        keepdims=0,
    )

    graph = helper.make_graph(
        nodes=[abs_node, mean_node],
        name="edgepulse_anomaly_score_model",
        inputs=[input_tensor],
        outputs=[output_tensor],
    )

    model = helper.make_model(
        graph,
        producer_name="edgepulse-ai-runtime",
        opset_imports=[helper.make_opsetid("", 13)],
    )

    onnx.checker.check_model(model)
    onnx.save(model, model_path)

    print(f"Created {model_path}")


if __name__ == "__main__":
    main()
