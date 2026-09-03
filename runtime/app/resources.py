from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prometheus_client.core import GaugeMetricFamily

CGROUP_ROOT = Path("/sys/fs/cgroup")


@dataclass(frozen=True)
class ResourceSnapshot:
    cgroup_v2_available: bool
    memory_current_bytes: int | None
    memory_peak_bytes: int | None
    memory_limit_bytes: int | None
    cpu_limit_cores: float | None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _read_int(path: Path) -> int | None:
    value = _read_text(path)

    if value is None or value == "max":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _read_cpu_limit(root: Path) -> float | None:
    value = _read_text(root / "cpu.max")

    if value is None:
        return None

    parts = value.split()

    if len(parts) != 2:
        return None

    quota, period = parts

    if quota == "max":
        return None

    try:
        quota_value = int(quota)
        period_value = int(period)
    except ValueError:
        return None

    if period_value <= 0:
        return None

    return quota_value / period_value


def read_resource_snapshot(
    root: Path = CGROUP_ROOT,
) -> ResourceSnapshot:
    cgroup_v2_available = (root / "cgroup.controllers").exists()

    if not cgroup_v2_available:
        return ResourceSnapshot(
            cgroup_v2_available=False,
            memory_current_bytes=None,
            memory_peak_bytes=None,
            memory_limit_bytes=None,
            cpu_limit_cores=None,
        )

    return ResourceSnapshot(
        cgroup_v2_available=True,
        memory_current_bytes=_read_int(root / "memory.current"),
        memory_peak_bytes=_read_int(root / "memory.peak"),
        memory_limit_bytes=_read_int(root / "memory.max"),
        cpu_limit_cores=_read_cpu_limit(root),
    )


class ResourceCollector:
    def __init__(self, root: Path = CGROUP_ROOT) -> None:
        self.root = root

    def collect(self):
        snapshot = read_resource_snapshot(self.root)

        yield GaugeMetricFamily(
            "edgepulse_resource_cgroup_v2_available",
            "Whether Linux cgroup v2 resource metrics are available.",
            value=float(snapshot.cgroup_v2_available),
        )

        if snapshot.memory_current_bytes is not None:
            yield GaugeMetricFamily(
                "edgepulse_resource_memory_current_bytes",
                "Current memory consumed by the runtime cgroup.",
                value=snapshot.memory_current_bytes,
            )

        if snapshot.memory_peak_bytes is not None:
            yield GaugeMetricFamily(
                "edgepulse_resource_memory_peak_bytes",
                "Peak memory consumed by the runtime cgroup.",
                value=snapshot.memory_peak_bytes,
            )

        memory_limited = snapshot.memory_limit_bytes is not None

        yield GaugeMetricFamily(
            "edgepulse_resource_memory_limited",
            "Whether the runtime cgroup has a finite memory limit.",
            value=float(memory_limited),
        )

        if (
            snapshot.memory_limit_bytes is not None
            and snapshot.memory_current_bytes is not None
        ):
            memory_limit = snapshot.memory_limit_bytes
            memory_current = snapshot.memory_current_bytes

            yield GaugeMetricFamily(
                "edgepulse_resource_memory_limit_bytes",
                "Configured cgroup memory limit.",
                value=memory_limit,
            )

            yield GaugeMetricFamily(
                "edgepulse_resource_memory_headroom_bytes",
                "Memory remaining before the cgroup memory limit.",
                value=max(0, memory_limit - memory_current),
            )

            utilization = memory_current / memory_limit if memory_limit > 0 else 0.0

            yield GaugeMetricFamily(
                "edgepulse_resource_memory_utilization_ratio",
                "Current memory usage as a ratio of the cgroup limit.",
                value=utilization,
            )

        cpu_limited = snapshot.cpu_limit_cores is not None

        yield GaugeMetricFamily(
            "edgepulse_resource_cpu_limited",
            "Whether the runtime cgroup has a finite CPU quota.",
            value=float(cpu_limited),
        )

        if snapshot.cpu_limit_cores is not None:
            yield GaugeMetricFamily(
                "edgepulse_resource_cpu_limit_cores",
                "Configured cgroup CPU quota expressed as CPU cores.",
                value=snapshot.cpu_limit_cores,
            )
