import pytest

from scripts.edgepulse_top import (
    LiveStats,
    MetricSnapshot,
    RuntimeSnapshot,
    derive_live_stats,
    parse_metrics,
    render_snapshot,
)

METRICS = """
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 12.5

# TYPE edgepulse_resource_cpu_limit_cores gauge
edgepulse_resource_cpu_limit_cores 0.5

# TYPE edgepulse_resource_memory_current_bytes gauge
edgepulse_resource_memory_current_bytes 67108864

# TYPE edgepulse_resource_memory_limit_bytes gauge
edgepulse_resource_memory_limit_bytes 536870912

# TYPE edgepulse_resource_memory_headroom_bytes gauge
edgepulse_resource_memory_headroom_bytes 469762048

# TYPE edgepulse_resource_memory_utilization_ratio gauge
edgepulse_resource_memory_utilization_ratio 0.125

# TYPE edgepulse_inference_requests_total counter
edgepulse_inference_requests_total{device_type="vibration"} 100
edgepulse_inference_requests_total{device_type="temperature"} 50

# TYPE edgepulse_inference_errors_total counter
edgepulse_inference_errors_total{device_type="vibration"} 2

# TYPE edgepulse_inference_in_progress gauge
edgepulse_inference_in_progress 3

# TYPE edgepulse_mqtt_connected gauge
edgepulse_mqtt_connected 1

# TYPE edgepulse_mqtt_messages_total counter
edgepulse_mqtt_messages_total{topic="edge/test"} 80

# TYPE edgepulse_mqtt_errors_total counter
edgepulse_mqtt_errors_total{topic="edge/test"} 1

# TYPE edgepulse_model_artifact_size_bytes gauge
edgepulse_model_artifact_size_bytes 270
"""


def test_render_snapshot() -> None:
    metrics = MetricSnapshot(
        collected_at=10.0,
        process_cpu_seconds=5.0,
        cpu_limit_cores=0.5,
        memory_current_bytes=64 * 1024 * 1024,
        memory_limit_bytes=512 * 1024 * 1024,
        memory_headroom_bytes=448 * 1024 * 1024,
        memory_utilization_ratio=0.125,
        inference_requests_total=100,
        inference_errors_total=2,
        inference_in_progress=2,
        inference_latency_buckets=(),
        mqtt_connected=1,
        mqtt_messages_total=80,
        mqtt_errors_total=1,
        model_artifact_size_bytes=270,
    )

    snapshot = RuntimeSnapshot(
        health_status="ok",
        service="edgepulse-ai-runtime",
        readiness_status="ready",
        readiness_error=None,
        model_name="edgepulse-anomaly-detector",
        model_version="0.9.0",
        model_backend="onnx",
        execution_profile="eco",
        execution_profile_active=True,
        metrics=metrics,
    )

    stats = LiveStats(
        interval_seconds=2.0,
        cpu_cores=0.45,
        cpu_budget_utilization_ratio=0.9,
        inference_requests_per_second=480.0,
        inference_errors_per_second=0.0,
        mqtt_messages_per_second=10.0,
        mqtt_errors_per_second=0.0,
        inference_latency_p50_seconds=0.00015,
        inference_latency_p95_seconds=0.00042,
        inference_latency_p99_seconds=0.0008,
    )

    output = render_snapshot(
        snapshot,
        stats,
        refresh_interval=2.0,
    )

    assert "Health       OK" in output
    assert "Readiness    READY" in output
    assert "MQTT         CONNECTED" in output

    assert "Backend      onnx" in output
    assert "Profile      eco (active)" in output

    assert "0.450 cores" in output
    assert "0.500 cores" in output
    assert "90.0%" in output

    assert "64.0 MiB" in output
    assert "512.0 MiB" in output
    assert "448.0 MiB" in output

    assert "480.00/s" in output
    assert "concurrency 2" in output

    assert "0.150 ms" in output
    assert "0.420 ms" in output
    assert "0.800 ms" in output

    assert "refresh 2.0s" in output


def test_parse_metrics() -> None:
    snapshot = parse_metrics(
        METRICS,
        collected_at=100.0,
    )

    assert snapshot.collected_at == 100.0

    assert snapshot.process_cpu_seconds == 12.5
    assert snapshot.cpu_limit_cores == 0.5

    assert snapshot.memory_current_bytes == 67108864
    assert snapshot.memory_limit_bytes == 536870912
    assert snapshot.memory_headroom_bytes == 469762048
    assert snapshot.memory_utilization_ratio == 0.125

    assert snapshot.inference_requests_total == 150
    assert snapshot.inference_errors_total == 2
    assert snapshot.inference_in_progress == 3
    assert snapshot.inference_latency_buckets == ()

    assert snapshot.mqtt_connected == 1
    assert snapshot.mqtt_messages_total == 80
    assert snapshot.mqtt_errors_total == 1

    assert snapshot.model_artifact_size_bytes == 270


def test_derive_live_stats() -> None:
    previous = MetricSnapshot(
        collected_at=100.0,
        process_cpu_seconds=10.0,
        cpu_limit_cores=0.5,
        memory_current_bytes=60_000_000,
        memory_limit_bytes=536_870_912,
        memory_headroom_bytes=476_870_912,
        memory_utilization_ratio=0.11,
        inference_requests_total=100,
        inference_errors_total=2,
        inference_in_progress=1,
        inference_latency_buckets=(
            (0.001, 50),
            (0.002, 90),
            (0.005, 100),
            (float("inf"), 100),
        ),
        mqtt_connected=1,
        mqtt_messages_total=80,
        mqtt_errors_total=1,
        model_artifact_size_bytes=270,
    )

    current = MetricSnapshot(
        collected_at=102.0,
        process_cpu_seconds=10.8,
        cpu_limit_cores=0.5,
        memory_current_bytes=62_000_000,
        memory_limit_bytes=536_870_912,
        memory_headroom_bytes=474_870_912,
        memory_utilization_ratio=0.12,
        inference_requests_total=140,
        inference_errors_total=4,
        inference_in_progress=2,
        inference_latency_buckets=(
            (0.001, 70),
            (0.002, 125),
            (0.005, 140),
            (float("inf"), 140),
        ),
        mqtt_connected=1,
        mqtt_messages_total=100,
        mqtt_errors_total=3,
        model_artifact_size_bytes=270,
    )

    stats = derive_live_stats(
        previous,
        current,
    )

    assert stats.interval_seconds == 2.0

    assert stats.cpu_cores == pytest.approx(0.4)
    assert stats.cpu_budget_utilization_ratio == pytest.approx(0.8)

    assert stats.inference_requests_per_second == 20.0

    assert stats.inference_errors_per_second == 1.0

    assert stats.mqtt_messages_per_second == 10.0
    assert stats.mqtt_errors_per_second == 1.0

    assert stats.inference_latency_p50_seconds is not None
    assert stats.inference_latency_p95_seconds is not None
    assert stats.inference_latency_p99_seconds is not None


def test_live_stats_ignore_counter_reset() -> None:
    previous = MetricSnapshot(
        collected_at=10.0,
        process_cpu_seconds=20.0,
        cpu_limit_cores=0.5,
        memory_current_bytes=None,
        memory_limit_bytes=None,
        memory_headroom_bytes=None,
        memory_utilization_ratio=None,
        inference_requests_total=100,
        inference_errors_total=10,
        inference_in_progress=0,
        inference_latency_buckets=(),
        mqtt_connected=1,
        mqtt_messages_total=100,
        mqtt_errors_total=5,
        model_artifact_size_bytes=None,
    )

    current = MetricSnapshot(
        collected_at=12.0,
        process_cpu_seconds=1.0,
        cpu_limit_cores=0.5,
        memory_current_bytes=None,
        memory_limit_bytes=None,
        memory_headroom_bytes=None,
        memory_utilization_ratio=None,
        inference_requests_total=3,
        inference_errors_total=0,
        inference_in_progress=0,
        inference_latency_buckets=(),
        mqtt_connected=1,
        mqtt_messages_total=4,
        mqtt_errors_total=0,
        model_artifact_size_bytes=None,
    )

    stats = derive_live_stats(
        previous,
        current,
    )

    assert stats.cpu_cores is None

    assert stats.inference_requests_per_second is None

    assert stats.mqtt_messages_per_second is None


def test_parse_metrics_handles_missing_optional_metrics() -> None:
    snapshot = parse_metrics(
        """
        # TYPE edgepulse_inference_requests_total counter
        edgepulse_inference_requests_total 4
        """,
        collected_at=10.0,
    )

    assert snapshot.inference_requests_total == 4
    assert snapshot.process_cpu_seconds is None
    assert snapshot.cpu_limit_cores is None
    assert snapshot.memory_current_bytes is None
    assert snapshot.mqtt_connected is None
