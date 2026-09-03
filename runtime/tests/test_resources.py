from pathlib import Path

from app.resources import ResourceCollector, read_resource_snapshot


def _write(root: Path, name: str, value: str) -> None:
    (root / name).write_text(value, encoding="utf-8")


def test_reads_limited_cgroup_v2_resources(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "134217728")
    _write(tmp_path, "memory.peak", "201326592")
    _write(tmp_path, "memory.max", "536870912")
    _write(tmp_path, "cpu.max", "50000 100000")

    snapshot = read_resource_snapshot(tmp_path)

    assert snapshot.cgroup_v2_available is True
    assert snapshot.memory_current_bytes == 134217728
    assert snapshot.memory_peak_bytes == 201326592
    assert snapshot.memory_limit_bytes == 536870912
    assert snapshot.cpu_limit_cores == 0.5


def test_reads_unlimited_cgroup_v2_resources(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "104857600")
    _write(tmp_path, "memory.peak", "157286400")
    _write(tmp_path, "memory.max", "max")
    _write(tmp_path, "cpu.max", "max 100000")

    snapshot = read_resource_snapshot(tmp_path)

    assert snapshot.cgroup_v2_available is True
    assert snapshot.memory_current_bytes == 104857600
    assert snapshot.memory_peak_bytes == 157286400
    assert snapshot.memory_limit_bytes is None
    assert snapshot.cpu_limit_cores is None


def test_reports_cgroup_v2_unavailable(tmp_path: Path) -> None:
    snapshot = read_resource_snapshot(tmp_path)

    assert snapshot.cgroup_v2_available is False
    assert snapshot.memory_current_bytes is None
    assert snapshot.memory_peak_bytes is None
    assert snapshot.memory_limit_bytes is None
    assert snapshot.cpu_limit_cores is None


def test_handles_invalid_cpu_max(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "100")
    _write(tmp_path, "memory.peak", "200")
    _write(tmp_path, "memory.max", "300")
    _write(tmp_path, "cpu.max", "invalid")

    snapshot = read_resource_snapshot(tmp_path)

    assert snapshot.cpu_limit_cores is None


def _collect_values(root: Path) -> dict[str, float]:
    values: dict[str, float] = {}

    for family in ResourceCollector(root).collect():
        for sample in family.samples:
            values[sample.name] = sample.value

    return values


def test_collector_exposes_limited_resources(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "134217728")
    _write(tmp_path, "memory.peak", "201326592")
    _write(tmp_path, "memory.max", "536870912")
    _write(tmp_path, "cpu.max", "50000 100000")

    values = _collect_values(tmp_path)

    assert values["edgepulse_resource_cgroup_v2_available"] == 1.0

    assert values["edgepulse_resource_memory_current_bytes"] == 134217728
    assert values["edgepulse_resource_memory_peak_bytes"] == 201326592
    assert values["edgepulse_resource_memory_limited"] == 1.0
    assert values["edgepulse_resource_memory_limit_bytes"] == 536870912
    assert values["edgepulse_resource_memory_headroom_bytes"] == 402653184
    assert values["edgepulse_resource_memory_utilization_ratio"] == 0.25

    assert values["edgepulse_resource_cpu_limited"] == 1.0
    assert values["edgepulse_resource_cpu_limit_cores"] == 0.5


def test_collector_handles_unlimited_resources(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "104857600")
    _write(tmp_path, "memory.peak", "157286400")
    _write(tmp_path, "memory.max", "max")
    _write(tmp_path, "cpu.max", "max 100000")

    values = _collect_values(tmp_path)

    assert values["edgepulse_resource_cgroup_v2_available"] == 1.0
    assert values["edgepulse_resource_memory_limited"] == 0.0
    assert values["edgepulse_resource_cpu_limited"] == 0.0

    assert "edgepulse_resource_memory_limit_bytes" not in values
    assert "edgepulse_resource_memory_headroom_bytes" not in values
    assert "edgepulse_resource_memory_utilization_ratio" not in values
    assert "edgepulse_resource_cpu_limit_cores" not in values


def test_handles_invalid_memory_and_zero_cpu_period(tmp_path: Path) -> None:
    _write(tmp_path, "cgroup.controllers", "cpu memory")
    _write(tmp_path, "memory.current", "invalid")
    _write(tmp_path, "memory.peak", "invalid")
    _write(tmp_path, "memory.max", "max")
    _write(tmp_path, "cpu.max", "50000 0")

    snapshot = read_resource_snapshot(tmp_path)

    assert snapshot.memory_current_bytes is None
    assert snapshot.memory_peak_bytes is None
    assert snapshot.memory_limit_bytes is None
    assert snapshot.cpu_limit_cores is None
