from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or update the EdgePulse model manifest."
    )
    parser.add_argument(
        "--model-path",
        default="runtime/models/anomaly_score.onnx",
        help="Path to the model artifact.",
    )
    parser.add_argument(
        "--manifest-path",
        default="runtime/models/model-manifest.json",
        help="Path where the manifest will be written.",
    )
    parser.add_argument("--model-name", default="edgepulse-anomaly-detector")
    parser.add_argument("--model-version", default="0.8.0")
    parser.add_argument("--model-backend", default="onnxruntime")
    parser.add_argument("--model-format", default="onnx")
    parser.add_argument(
        "--description",
        default="Demo ONNX anomaly scoring model for EdgePulse runtime.",
    )

    args = parser.parse_args()

    model_path = Path(args.model_path)
    manifest_path = Path(args.manifest_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    manifest = {
        "model_name": args.model_name,
        "model_version": args.model_version,
        "model_backend": args.model_backend,
        "model_format": args.model_format,
        "model_path": str(model_path.relative_to(Path("runtime"))),
        "artifact_filename": model_path.name,
        "artifact_sha256": sha256_file(model_path),
        "artifact_size_bytes": model_path.stat().st_size,
        "generated_at": datetime.now(UTC).isoformat(),
        "description": args.description,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Wrote model manifest: {manifest_path}")
    print(f"SHA256: {manifest['artifact_sha256']}")


if __name__ == "__main__":
    main()
