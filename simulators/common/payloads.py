from __future__ import annotations

import random
from datetime import UTC, datetime


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def is_anomaly_event(anomaly_rate: float) -> bool:
    return random.random() < anomaly_rate


def normalized_feature_vector(
    anomaly: bool,
    size: int = 8,
    normal_min: float = 0.05,
    normal_max: float = 0.45,
    anomaly_min: float = 0.75,
    anomaly_max: float = 1.20,
) -> list[float]:
    if anomaly:
        return [round(random.uniform(anomaly_min, anomaly_max), 4) for _ in range(size)]

    return [round(random.uniform(normal_min, normal_max), 4) for _ in range(size)]
