from __future__ import annotations

import requests


def post_inference(endpoint: str, payload: dict, timeout_seconds: int = 5) -> dict:
    response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()
