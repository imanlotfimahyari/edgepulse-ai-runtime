from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import onnx
from onnx import TensorProto
from onnxruntime.quantization import (
    QuantType,
    quant_pre_process,
    quantize_dynamic,
)

DEFAULT_INPUT = Path("runtime/models/anomaly_score.onnx")

DEFAULT_OUTPUT = Path("runtime/models/anomaly_score_int8.onnx")


def quantize_model(
    input_path: Path,
    output_path: Path,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"FP32 model not found: {input_path}")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(prefix="edgepulse-quant-") as temporary_directory:
        preprocessed_path = Path(temporary_directory) / "preprocessed.onnx"

        quant_pre_process(
            input_model=input_path,
            output_model_path=preprocessed_path,
            skip_optimization=True,
            skip_symbolic_shape=True,
        )

        quantize_dynamic(
            model_input=preprocessed_path,
            model_output=output_path,
            per_channel=True,
            reduce_range=True,
            weight_type=QuantType.QInt8,
            op_types_to_quantize=[
                "MatMul",
            ],
        )

    model = onnx.load(output_path)

    onnx.checker.check_model(model)

    return output_path


def _count_quantized_initializers(
    model: onnx.ModelProto,
) -> int:
    return sum(
        initializer.data_type
        in {
            TensorProto.INT8,
            TensorProto.UINT8,
        }
        for initializer in model.graph.initializer
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a dynamically quantized INT8 variant of the EdgePulse ONNX model."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=(f"FP32 ONNX input model (default: {DEFAULT_INPUT})"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(f"INT8 ONNX output model (default: {DEFAULT_OUTPUT})"),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_path = quantize_model(
        args.input,
        args.output,
    )

    fp32_size = args.input.stat().st_size
    int8_size = output_path.stat().st_size

    reduction_ratio = 1.0 - int8_size / fp32_size

    model = onnx.load(output_path)

    quantized_initializers = _count_quantized_initializers(model)

    print(f"Created {output_path}")

    print(f"FP32 artifact: {fp32_size} bytes")

    print(f"INT8 artifact: {int8_size} bytes")

    print(f"Size reduction: {reduction_ratio * 100:.1f}%")

    print(f"Quantized initializers: {quantized_initializers}")


if __name__ == "__main__":
    main()
