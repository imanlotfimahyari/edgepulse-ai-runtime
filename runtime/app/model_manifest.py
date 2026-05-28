from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_model_manifest(
    manifest_path: str = "/app/models/model-manifest.json",
) -> dict[str, Any]:
    path = Path(manifest_path)

    if not path.exists():
        return {
            "model_manifest_available": False,
            "model_manifest_path": manifest_path,
        }

    manifest = json.loads(path.read_text())
    manifest["model_manifest_available"] = True
    manifest["model_manifest_path"] = manifest_path

    model_path_value = manifest.get("model_path")
    expected_sha256 = manifest.get("artifact_sha256")

    if model_path_value and expected_sha256:
        model_path = Path("/app") / str(model_path_value)

        if model_path.exists():
            actual_sha256 = sha256_file(model_path)
            manifest["artifact_sha256_verified"] = actual_sha256 == expected_sha256
        else:
            manifest["artifact_sha256_verified"] = False
            manifest["artifact_missing"] = True

    return manifest
