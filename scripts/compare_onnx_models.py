from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort

DEFAULT_FP32_MODEL = Path("runtime/models/anomaly_score.onnx")

DEFAULT_INT8_MODEL = Path("runtime/models/anomaly_score_int8.onnx")

DEFAULT_THRESHOLD = 0.65


def create_session(
    model_path: Path,
) -> ort.InferenceSession:
    return ort.InferenceSession(
        str(model_path),
        providers=[
            "CPUExecutionProvider",
        ],
    )


def infer(
    session: ort.InferenceSession,
    features: list[float],
) -> float:
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


def compare_models(
    fp32_path: Path,
    int8_path: Path,
    *,
    threshold: float,
    samples: int,
) -> dict[str, object]:
    fp32_session = create_session(fp32_path)

    int8_session = create_session(int8_path)

    absolute_errors: list[float] = []
    relative_errors: list[float] = []

    classification_mismatches = 0

    worst_score = 0.0
    worst_fp32 = 0.0
    worst_int8 = 0.0
    worst_error = -1.0

    scores = np.linspace(
        0.0,
        1.5,
        samples,
        dtype=np.float32,
    )

    for score in scores:
        #
        # A single-feature vector is sufficient
        # because the FP32 model first computes
        # mean(abs(features)).
        #
        features = [float(score)]

        fp32_score = infer(
            fp32_session,
            features,
        )

        int8_score = infer(
            int8_session,
            features,
        )

        absolute_error = abs(int8_score - fp32_score)

        absolute_errors.append(absolute_error)

        if abs(fp32_score) > 1e-12:
            relative_errors.append(absolute_error / abs(fp32_score))

        fp32_prediction = fp32_score >= threshold

        int8_prediction = int8_score >= threshold

        if fp32_prediction != int8_prediction:
            classification_mismatches += 1

        if absolute_error > worst_error:
            worst_error = absolute_error
            worst_score = float(score)
            worst_fp32 = fp32_score
            worst_int8 = int8_score

    error_array = np.asarray(
        absolute_errors,
        dtype=np.float64,
    )

    relative_array = np.asarray(
        relative_errors,
        dtype=np.float64,
    )

    fp32_size = fp32_path.stat().st_size

    int8_size = int8_path.stat().st_size

    return {
        "models": {
            "fp32": str(fp32_path),
            "int8": str(int8_path),
        },
        "artifacts": {
            "fp32_bytes": fp32_size,
            "int8_bytes": int8_size,
            "size_reduction_bytes": (fp32_size - int8_size),
            "size_reduction_percent": ((1.0 - int8_size / fp32_size) * 100),
        },
        "comparison": {
            "samples": samples,
            "score_range": [
                0.0,
                1.5,
            ],
            "threshold": threshold,
            "mean_absolute_error": float(np.mean(error_array)),
            "p95_absolute_error": float(
                np.percentile(
                    error_array,
                    95,
                )
            ),
            "max_absolute_error": float(np.max(error_array)),
            "mean_relative_error": (
                float(np.mean(relative_array)) if relative_array.size else None
            ),
            "max_relative_error": (
                float(np.max(relative_array)) if relative_array.size else None
            ),
            "classification_mismatches": (classification_mismatches),
            "classification_mismatch_ratio": (classification_mismatches / samples),
        },
        "worst_case": {
            "input_score": worst_score,
            "fp32_score": worst_fp32,
            "int8_score": worst_int8,
            "absolute_error": worst_error,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Compare FP32 and INT8 EdgePulse ONNX models."),
    )

    parser.add_argument(
        "--fp32",
        type=Path,
        default=DEFAULT_FP32_MODEL,
    )

    parser.add_argument(
        "--int8",
        type=Path,
        default=DEFAULT_INT8_MODEL,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=1501,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.samples < 2:
        raise ValueError("--samples must be at least 2")

    result = compare_models(
        args.fp32,
        args.int8,
        threshold=args.threshold,
        samples=args.samples,
    )

    rendered = json.dumps(
        result,
        indent=2,
    )

    print(rendered)

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(rendered + "\n")


if __name__ == "__main__":
    main()
