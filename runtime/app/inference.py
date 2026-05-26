from __future__ import annotations

from statistics import mean

from app.config import settings


def run_inference(features: list[float]) -> tuple[str, float, float]:
    """
    Simple rule-based anomaly detector.

    This is intentionally not an ML research model. It represents the first
    platform milestone: a stable runtime contract around inference execution.
    """
    normalized_features = [abs(value) for value in features]
    anomaly_score = mean(normalized_features)

    if anomaly_score >= settings.anomaly_threshold:
        prediction = "anomaly"
        confidence = min(0.99, 0.70 + anomaly_score / 3)
    else:
        prediction = "normal"
        confidence = max(0.50, 1 - anomaly_score)

    return prediction, round(anomaly_score, 4), round(confidence, 4)
