from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.model_manifest import (
    load_model_manifest,
)


def _sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(
    manifest_path: Path,
    model_path: Path,
    *,
    artifact_sha256: str,
) -> None:
    runtime_root = manifest_path.parent.parent

    relative_model_path = model_path.relative_to(runtime_root)

    manifest = {
        "model_name": ("edgepulse-anomaly-detector"),
        "model_version": "0.9.0",
        "model_backend": "onnxruntime",
        "model_format": "onnx",
        "model_path": str(relative_model_path),
        "artifact_filename": (model_path.name),
        "artifact_sha256": (artifact_sha256),
        "artifact_size_bytes": (model_path.stat().st_size),
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        )
        + "\n"
    )


def test_manifest_verifies_active_model(
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"

    models_dir.mkdir()

    model_path = models_dir / "anomaly_score.onnx"

    model_path.write_bytes(b"edgepulse-fp32-model")

    manifest_path = models_dir / "model-manifest.json"

    _write_manifest(
        manifest_path,
        model_path,
        artifact_sha256=_sha256(model_path),
    )

    manifest = load_model_manifest(
        str(manifest_path),
        active_model_path=str(model_path),
    )

    assert manifest["model_manifest_available"] is True

    assert manifest["artifact_sha256_verified"] is True

    assert manifest["active_model_matches_manifest"] is True


def test_manifest_detects_wrong_active_model(
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"

    models_dir.mkdir()

    fp32_path = models_dir / "anomaly_score.onnx"

    int8_path = models_dir / "anomaly_score_int8.onnx"

    fp32_path.write_bytes(b"fp32")

    int8_path.write_bytes(b"int8")

    manifest_path = models_dir / "model-manifest.json"

    _write_manifest(
        manifest_path,
        fp32_path,
        artifact_sha256=_sha256(fp32_path),
    )

    manifest = load_model_manifest(
        str(manifest_path),
        active_model_path=str(int8_path),
    )

    assert manifest["artifact_sha256_verified"] is True

    assert manifest["active_model_matches_manifest"] is False


def test_manifest_detects_corrupt_artifact(
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"

    models_dir.mkdir()

    model_path = models_dir / "anomaly_score.onnx"

    model_path.write_bytes(b"original-model")

    manifest_path = models_dir / "model-manifest.json"

    original_sha256 = _sha256(model_path)

    _write_manifest(
        manifest_path,
        model_path,
        artifact_sha256=(original_sha256),
    )

    model_path.write_bytes(b"modified-model")

    manifest = load_model_manifest(
        str(manifest_path),
        active_model_path=str(model_path),
    )

    assert manifest["artifact_sha256_verified"] is False

    assert manifest["active_model_matches_manifest"] is True


def test_missing_manifest_is_reported(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "models" / "missing.json"

    manifest = load_model_manifest(str(manifest_path))

    assert manifest == {
        "model_manifest_available": False,
        "model_manifest_path": str(manifest_path),
    }
