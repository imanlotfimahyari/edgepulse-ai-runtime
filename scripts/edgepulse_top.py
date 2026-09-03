from __future__ import annotations

import argparse
import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from prometheus_client.parser import text_string_to_metric_families
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

DEFAULT_BASE_URL = "http://host.docker.internal:8080"
DEFAULT_TIMEOUT = 3.0
DEFAULT_INTERVAL = 2.0

SPARK_BLOCKS = "▁▂▃▄▅▆▇█"

console = Console()


@dataclass(frozen=True)
class MetricSnapshot:
    collected_at: float

    process_cpu_seconds: float | None
    cpu_limit_cores: float | None

    memory_current_bytes: float | None
    memory_limit_bytes: float | None
    memory_headroom_bytes: float | None
    memory_utilization_ratio: float | None

    inference_requests_total: float
    inference_errors_total: float
    inference_in_progress: float | None

    inference_latency_buckets: tuple[
        tuple[float, float],
        ...,
    ]

    mqtt_connected: float | None
    mqtt_messages_total: float
    mqtt_errors_total: float

    model_artifact_size_bytes: float | None


@dataclass(frozen=True)
class RuntimeSnapshot:
    health_status: str
    service: str | None

    readiness_status: str
    readiness_error: str | None

    model_name: str | None
    model_version: str | None
    model_backend: str | None

    execution_profile: str | None
    execution_profile_active: bool

    metrics: MetricSnapshot


@dataclass(frozen=True)
class LiveStats:
    interval_seconds: float

    cpu_cores: float | None
    cpu_budget_utilization_ratio: float | None

    inference_requests_per_second: float | None
    inference_errors_per_second: float | None

    mqtt_messages_per_second: float | None
    mqtt_errors_per_second: float | None

    inference_latency_p50_seconds: float | None
    inference_latency_p95_seconds: float | None
    inference_latency_p99_seconds: float | None


class DashboardHistory:
    def __init__(
        self,
        size: int = 30,
    ) -> None:
        self.cpu: deque[float] = deque(
            maxlen=size,
        )
        self.inference_rate: deque[float] = deque(
            maxlen=size,
        )

    def add(
        self,
        stats: LiveStats,
    ) -> None:
        if stats.cpu_budget_utilization_ratio is not None:
            self.cpu.append(
                stats.cpu_budget_utilization_ratio,
            )

        if stats.inference_requests_per_second is not None:
            self.inference_rate.append(
                stats.inference_requests_per_second,
            )


def _get_json(
    base_url: str,
    path: str,
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        body = exc.read().decode("utf-8")

        try:
            return json.loads(body)
        except json.JSONDecodeError as json_exc:
            raise RuntimeError(f"{path} returned HTTP {exc.code}: {body}") from json_exc

    except URLError as exc:
        raise RuntimeError(
            f"Unable to reach EdgePulse at {base_url}: {exc.reason}"
        ) from exc


def _get_text(
    base_url: str,
    path: str,
    timeout: float,
) -> str:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"Accept": "text/plain"},
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return response.read().decode("utf-8")

    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Unable to read {path} from {base_url}: {exc}") from exc


def _samples_by_name(
    metrics_text: str,
) -> dict[str, list[float]]:
    samples: dict[str, list[float]] = {}

    for family in text_string_to_metric_families(metrics_text):
        for sample in family.samples:
            samples.setdefault(
                sample.name,
                [],
            ).append(float(sample.value))

    return samples


def _single_metric(
    samples: dict[str, list[float]],
    name: str,
) -> float | None:
    values = samples.get(name)

    if not values:
        return None

    return values[0]


def _metric_total(
    samples: dict[str, list[float]],
    name: str,
) -> float:
    return sum(
        samples.get(
            name,
            [],
        )
    )


def _histogram_buckets(
    metrics_text: str,
    metric_name: str,
) -> tuple[tuple[float, float], ...]:
    totals: dict[float, float] = {}

    bucket_name = f"{metric_name}_bucket"

    for family in text_string_to_metric_families(metrics_text):
        for sample in family.samples:
            if sample.name != bucket_name:
                continue

            upper_bound_text = sample.labels.get("le")

            if upper_bound_text is None:
                continue

            if upper_bound_text == "+Inf":
                upper_bound = float("inf")
            else:
                try:
                    upper_bound = float(upper_bound_text)
                except ValueError:
                    continue

            totals[upper_bound] = totals.get(
                upper_bound,
                0.0,
            ) + float(sample.value)

    return tuple(
        sorted(
            totals.items(),
            key=lambda item: item[0],
        )
    )


def parse_metrics(
    metrics_text: str,
    *,
    collected_at: float | None = None,
) -> MetricSnapshot:
    samples = _samples_by_name(metrics_text)

    return MetricSnapshot(
        collected_at=(time.monotonic() if collected_at is None else collected_at),
        process_cpu_seconds=_single_metric(
            samples,
            "process_cpu_seconds_total",
        ),
        cpu_limit_cores=_single_metric(
            samples,
            "edgepulse_resource_cpu_limit_cores",
        ),
        memory_current_bytes=_single_metric(
            samples,
            "edgepulse_resource_memory_current_bytes",
        ),
        memory_limit_bytes=_single_metric(
            samples,
            "edgepulse_resource_memory_limit_bytes",
        ),
        memory_headroom_bytes=_single_metric(
            samples,
            "edgepulse_resource_memory_headroom_bytes",
        ),
        memory_utilization_ratio=_single_metric(
            samples,
            "edgepulse_resource_memory_utilization_ratio",
        ),
        inference_requests_total=_metric_total(
            samples,
            "edgepulse_inference_requests_total",
        ),
        inference_errors_total=_metric_total(
            samples,
            "edgepulse_inference_errors_total",
        ),
        inference_in_progress=_single_metric(
            samples,
            "edgepulse_inference_in_progress",
        ),
        inference_latency_buckets=_histogram_buckets(
            metrics_text,
            "edgepulse_inference_latency_seconds",
        ),
        mqtt_connected=_single_metric(
            samples,
            "edgepulse_mqtt_connected",
        ),
        mqtt_messages_total=_metric_total(
            samples,
            "edgepulse_mqtt_messages_total",
        ),
        mqtt_errors_total=_metric_total(
            samples,
            "edgepulse_mqtt_errors_total",
        ),
        model_artifact_size_bytes=_single_metric(
            samples,
            "edgepulse_model_artifact_size_bytes",
        ),
    )


def _counter_rate(
    previous: float | None,
    current: float | None,
    interval_seconds: float,
) -> float | None:
    if previous is None or current is None or interval_seconds <= 0:
        return None

    delta = current - previous

    if delta < 0:
        return None

    return delta / interval_seconds


def _histogram_delta(
    previous: tuple[tuple[float, float], ...],
    current: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...] | None:
    previous_map = dict(previous)
    current_map = dict(current)

    if not previous_map or not current_map:
        return None

    if previous_map.keys() != current_map.keys():
        return None

    result: list[tuple[float, float]] = []

    for upper_bound in sorted(current_map):
        delta = current_map[upper_bound] - previous_map[upper_bound]

        if delta < 0:
            return None

        result.append(
            (
                upper_bound,
                delta,
            )
        )

    return tuple(result)


def _histogram_quantile(
    quantile: float,
    buckets: tuple[tuple[float, float], ...],
) -> float | None:
    if not buckets:
        return None

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1")

    total = buckets[-1][1]

    if total <= 0:
        return None

    rank = quantile * total

    previous_bound = 0.0
    previous_count = 0.0

    for (
        upper_bound,
        cumulative_count,
    ) in buckets:
        if cumulative_count < rank:
            previous_bound = upper_bound
            previous_count = cumulative_count
            continue

        if upper_bound == float("inf"):
            if previous_bound == float("inf"):
                return None

            return previous_bound

        bucket_count = cumulative_count - previous_count

        if bucket_count <= 0:
            return upper_bound

        position = (rank - previous_count) / bucket_count

        return previous_bound + (upper_bound - previous_bound) * position

    return None


def derive_live_stats(
    previous: MetricSnapshot,
    current: MetricSnapshot,
) -> LiveStats:
    interval_seconds = current.collected_at - previous.collected_at

    cpu_cores = _counter_rate(
        previous.process_cpu_seconds,
        current.process_cpu_seconds,
        interval_seconds,
    )

    cpu_budget_utilization_ratio = None

    if (
        cpu_cores is not None
        and current.cpu_limit_cores is not None
        and current.cpu_limit_cores > 0
    ):
        cpu_budget_utilization_ratio = cpu_cores / current.cpu_limit_cores

    histogram_delta = _histogram_delta(
        previous.inference_latency_buckets,
        current.inference_latency_buckets,
    )

    if histogram_delta is None:
        latency_p50 = None
        latency_p95 = None
        latency_p99 = None
    else:
        latency_p50 = _histogram_quantile(
            0.50,
            histogram_delta,
        )
        latency_p95 = _histogram_quantile(
            0.95,
            histogram_delta,
        )
        latency_p99 = _histogram_quantile(
            0.99,
            histogram_delta,
        )

    return LiveStats(
        interval_seconds=interval_seconds,
        cpu_cores=cpu_cores,
        cpu_budget_utilization_ratio=(cpu_budget_utilization_ratio),
        inference_requests_per_second=_counter_rate(
            previous.inference_requests_total,
            current.inference_requests_total,
            interval_seconds,
        ),
        inference_errors_per_second=_counter_rate(
            previous.inference_errors_total,
            current.inference_errors_total,
            interval_seconds,
        ),
        mqtt_messages_per_second=_counter_rate(
            previous.mqtt_messages_total,
            current.mqtt_messages_total,
            interval_seconds,
        ),
        mqtt_errors_per_second=_counter_rate(
            previous.mqtt_errors_total,
            current.mqtt_errors_total,
            interval_seconds,
        ),
        inference_latency_p50_seconds=latency_p50,
        inference_latency_p95_seconds=latency_p95,
        inference_latency_p99_seconds=latency_p99,
    )


def _format_mib(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value / 1024 / 1024:.1f} MiB"


def _format_size(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    if value < 1024:
        return f"{value:.0f} B"

    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"

    return f"{value / 1024 / 1024:.1f} MiB"


def _format_rate(
    value: float | None,
) -> str:
    if value is None:
        return "warming up"

    return f"{value:.2f}/s"


def _format_latency_ms(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value * 1000:.3f} ms"


def _format_percent(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value * 100:.1f}%"


def _mqtt_state(
    value: float | None,
) -> str:
    if value is None:
        return "unavailable"

    if value >= 1:
        return "CONNECTED"

    return "DISCONNECTED"


def _cpu_style(
    ratio: float | None,
) -> str:
    if ratio is None:
        return "dim"

    if ratio >= 1.0:
        return "bold red"

    if ratio >= 0.85:
        return "yellow"

    return "green"


def _memory_style(
    ratio: float | None,
) -> str:
    if ratio is None:
        return "dim"

    if ratio >= 0.90:
        return "bold red"

    if ratio >= 0.75:
        return "yellow"

    return "green"


def _usage_bar(
    ratio: float | None,
    *,
    style: str,
    width: int = 20,
) -> Text:
    if ratio is None:
        return Text(
            "─" * width,
            style="dim",
        )

    bounded = min(
        max(ratio, 0.0),
        1.0,
    )

    filled = round(bounded * width)

    empty = width - filled

    bar = Text()

    bar.append(
        "█" * filled,
        style=style,
    )

    bar.append(
        "░" * empty,
        style="dim",
    )

    return bar


def _status_badge(
    label: str,
    healthy: bool,
) -> Text:
    style = "bold green" if healthy else "bold red"

    badge = Text()

    badge.append(
        "● ",
        style=style,
    )

    badge.append(
        label,
        style=style,
    )

    return badge


def _sparkline(
    values: deque[float],
    *,
    maximum: float | None = None,
    style: str = "cyan",
) -> Text:
    if not values:
        return Text(
            "·",
            style="dim",
        )

    data = list(values)

    lower = 0.0

    upper = maximum if maximum is not None else max(data)

    if upper <= lower:
        upper = 1.0

    output = Text()

    for value in data:
        normalized = (value - lower) / (upper - lower)

        normalized = min(
            max(
                normalized,
                0.0,
            ),
            1.0,
        )

        index = round(normalized * (len(SPARK_BLOCKS) - 1))

        output.append(
            SPARK_BLOCKS[index],
            style=style,
        )

    return output


def render_snapshot(
    snapshot: RuntimeSnapshot,
    stats: LiveStats | None = None,
    *,
    refresh_interval: float | None = None,
) -> str:
    metrics = snapshot.metrics

    cpu_usage = "warming up"
    cpu_utilization = "warming up"

    inference_rate = "warming up"
    inference_error_rate = "warming up"

    mqtt_rate = "warming up"
    mqtt_error_rate = "warming up"

    latency_p50 = "n/a"
    latency_p95 = "n/a"
    latency_p99 = "n/a"

    if stats is not None:
        if stats.cpu_cores is not None:
            cpu_usage = f"{stats.cpu_cores:.3f} cores"

        cpu_utilization = _format_percent(stats.cpu_budget_utilization_ratio)

        inference_rate = _format_rate(stats.inference_requests_per_second)

        inference_error_rate = _format_rate(stats.inference_errors_per_second)

        mqtt_rate = _format_rate(stats.mqtt_messages_per_second)

        mqtt_error_rate = _format_rate(stats.mqtt_errors_per_second)

        latency_p50 = _format_latency_ms(stats.inference_latency_p50_seconds)

        latency_p95 = _format_latency_ms(stats.inference_latency_p95_seconds)

        latency_p99 = _format_latency_ms(stats.inference_latency_p99_seconds)

    cpu_budget = (
        f"{metrics.cpu_limit_cores:.3f} cores"
        if metrics.cpu_limit_cores is not None
        else "unlimited"
    )

    inference_concurrency = (
        f"{metrics.inference_in_progress:.0f}"
        if metrics.inference_in_progress is not None
        else "n/a"
    )

    lines = [
        "EdgePulse Top",
        "=" * 60,
        (f"Health       {snapshot.health_status.upper()}"),
        (f"Readiness    {snapshot.readiness_status.upper()}"),
        (f"MQTT         {_mqtt_state(metrics.mqtt_connected)}"),
    ]

    if snapshot.readiness_error:
        lines.append(f"Ready error  {snapshot.readiness_error}")

    profile = snapshot.execution_profile or "n/a"

    if snapshot.execution_profile_active:
        profile += " (active)"

    lines.extend(
        [
            "",
            (f"Model        {snapshot.model_name or 'n/a'}"),
            (f"Version      {snapshot.model_version or 'n/a'}"),
            (f"Backend      {snapshot.model_backend or 'n/a'}"),
            f"Profile      {profile}",
            (f"Artifact     {_format_size(metrics.model_artifact_size_bytes)}"),
            "",
            "Resources",
            "-" * 60,
            (f"CPU          {cpu_utilization:<10} {cpu_usage} / {cpu_budget}"),
            (
                f"Memory       "
                f"{_format_percent(metrics.memory_utilization_ratio):<10} "
                f"{_format_mib(metrics.memory_current_bytes)} / "
                f"{_format_mib(metrics.memory_limit_bytes)}"
            ),
            (f"Headroom     {_format_mib(metrics.memory_headroom_bytes)}"),
            "",
            "Traffic",
            "-" * 60,
            (f"Inference    {inference_rate:<14} concurrency {inference_concurrency}"),
            (f"Infer errors {inference_error_rate}"),
            (f"MQTT         {mqtt_rate:<14} errors {mqtt_error_rate}"),
            "",
            "Inference latency",
            "-" * 60,
            f"p50          {latency_p50}",
            f"p95          {latency_p95}",
            f"p99          {latency_p99}",
        ]
    )

    if refresh_interval is not None:
        lines.extend(
            [
                "",
                "-" * 60,
                (f"refresh {refresh_interval:.1f}s | Ctrl-C to quit"),
            ]
        )

    return "\n".join(lines)


def build_dashboard(
    snapshot: RuntimeSnapshot,
    stats: LiveStats | None,
    refresh_interval: float,
    *,
    poll_failures: int = 0,
    poll_error: str | None = None,
    history: DashboardHistory | None = None,
) -> RenderableType:
    metrics = snapshot.metrics

    ready = snapshot.readiness_status == "ready"

    mqtt_connected = metrics.mqtt_connected is not None and metrics.mqtt_connected >= 1

    if poll_failures == 0:
        telemetry_status = Text(
            "● LIVE",
            style="bold green",
        )

    elif poll_failures < 3:
        telemetry_status = Text(
            (f"● DEGRADED ({poll_failures})"),
            style="bold yellow",
        )

    else:
        telemetry_status = Text(
            (f"● UNREACHABLE ({poll_failures})"),
            style="bold red",
        )

    header = Table.grid(
        expand=True,
    )

    header.add_column()
    header.add_column(
        justify="center",
    )
    header.add_column(
        justify="center",
    )
    header.add_column(
        justify="right",
    )

    header.add_row(
        _status_badge(
            ("READY" if ready else "NOT READY"),
            ready,
        ),
        _status_badge(
            ("MQTT CONNECTED" if mqtt_connected else "MQTT DISCONNECTED"),
            mqtt_connected,
        ),
        telemetry_status,
        Text(
            f"refresh {refresh_interval:.1f}s",
            style="dim",
        ),
    )

    runtime_table = Table.grid(
        padding=(0, 2),
    )

    runtime_table.add_column(
        style="dim",
    )
    runtime_table.add_column()

    runtime_table.add_row(
        "Service",
        snapshot.service or "n/a",
    )

    runtime_table.add_row(
        "Version",
        snapshot.model_version or "n/a",
    )

    runtime_table.add_row(
        "Health",
        _status_badge(
            snapshot.health_status.upper(),
            snapshot.health_status == "ok",
        ),
    )

    runtime_table.add_row(
        "Readiness",
        _status_badge(
            snapshot.readiness_status.upper(),
            ready,
        ),
    )

    model_table = Table.grid(
        padding=(0, 2),
    )

    model_table.add_column(
        style="dim",
    )
    model_table.add_column(
        style="cyan",
    )

    model_table.add_row(
        "Model",
        snapshot.model_name or "n/a",
    )

    model_table.add_row(
        "Backend",
        (snapshot.model_backend.upper() if snapshot.model_backend else "n/a"),
    )

    profile = snapshot.execution_profile or "n/a"

    if snapshot.execution_profile_active:
        profile += " (active)"

    model_table.add_row(
        "Profile",
        profile,
    )

    model_table.add_row(
        "Artifact",
        _format_size(metrics.model_artifact_size_bytes),
    )

    cpu_ratio = stats.cpu_budget_utilization_ratio if stats is not None else None

    memory_ratio = metrics.memory_utilization_ratio

    cpu_style = _cpu_style(cpu_ratio)

    memory_style = _memory_style(memory_ratio)

    cpu_current = (
        f"{stats.cpu_cores:.3f}"
        if (stats is not None and stats.cpu_cores is not None)
        else "warming up"
    )

    cpu_limit = (
        f"{metrics.cpu_limit_cores:.3f}" if metrics.cpu_limit_cores is not None else "∞"
    )

    resources = Table.grid(
        expand=True,
        padding=(0, 1),
    )

    resources.add_column(
        width=9,
        style="dim",
    )

    resources.add_column(
        justify="right",
        width=8,
    )

    resources.add_column(
        width=22,
    )

    resources.add_column(
        ratio=1,
    )

    resources.add_row(
        "CPU",
        Text(
            _format_percent(cpu_ratio),
            style=cpu_style,
        ),
        _usage_bar(
            cpu_ratio,
            style=cpu_style,
        ),
        (f"{cpu_current} / {cpu_limit} cores"),
    )

    resources.add_row(
        "Memory",
        Text(
            _format_percent(memory_ratio),
            style=memory_style,
        ),
        _usage_bar(
            memory_ratio,
            style=memory_style,
        ),
        (
            f"{_format_mib(metrics.memory_current_bytes)} "
            f"/ "
            f"{_format_mib(metrics.memory_limit_bytes)}"
        ),
    )

    resources.add_row(
        "Headroom",
        "",
        "",
        _format_mib(metrics.memory_headroom_bytes),
    )

    inference_table = Table.grid(
        padding=(0, 2),
    )

    inference_table.add_column(
        style="dim",
    )

    inference_table.add_column(
        justify="right",
        style="cyan",
    )

    inference_table.add_row(
        "Rate",
        (_format_rate(stats.inference_requests_per_second) if stats else "warming up"),
    )

    inference_table.add_row(
        "Concurrency",
        (
            f"{metrics.inference_in_progress:.0f}"
            if metrics.inference_in_progress is not None
            else "n/a"
        ),
    )

    inference_table.add_row(
        "Errors",
        (_format_rate(stats.inference_errors_per_second) if stats else "warming up"),
    )

    mqtt_table = Table.grid(
        padding=(0, 2),
    )

    mqtt_table.add_column(
        style="dim",
    )

    mqtt_table.add_column(
        justify="right",
    )

    mqtt_table.add_row(
        "State",
        _status_badge(
            ("CONNECTED" if mqtt_connected else "DISCONNECTED"),
            mqtt_connected,
        ),
    )

    mqtt_table.add_row(
        "Rate",
        Text(
            (_format_rate(stats.mqtt_messages_per_second) if stats else "warming up"),
            style="cyan",
        ),
    )

    mqtt_table.add_row(
        "Errors",
        (_format_rate(stats.mqtt_errors_per_second) if stats else "warming up"),
    )

    latency_table = Table(
        expand=True,
        box=None,
        show_header=True,
        header_style="dim",
    )

    latency_table.add_column(
        "p50",
        justify="center",
    )

    latency_table.add_column(
        "p95",
        justify="center",
    )

    latency_table.add_column(
        "p99",
        justify="center",
    )

    latency_table.add_row(
        Text(
            (
                _format_latency_ms(stats.inference_latency_p50_seconds)
                if stats
                else "n/a"
            ),
            style="cyan",
        ),
        Text(
            (
                _format_latency_ms(stats.inference_latency_p95_seconds)
                if stats
                else "n/a"
            ),
            style="cyan",
        ),
        Text(
            (
                _format_latency_ms(stats.inference_latency_p99_seconds)
                if stats
                else "n/a"
            ),
            style="cyan",
        ),
    )

    trends = Table.grid(
        expand=True,
        padding=(0, 2),
    )

    trends.add_column(
        width=10,
        style="dim",
    )

    trends.add_column()

    trends.add_column(
        justify="right",
        width=14,
    )

    if history is not None:
        cpu_history = _sparkline(
            history.cpu,
            maximum=1.0,
            style=(_cpu_style(cpu_ratio) if cpu_ratio is not None else "cyan"),
        )

        inference_history = _sparkline(
            history.inference_rate,
            style="cyan",
        )

    else:
        cpu_history = Text(
            "·",
            style="dim",
        )

        inference_history = Text(
            "·",
            style="dim",
        )

    current_cpu = _format_percent(cpu_ratio)

    current_inference = (
        _format_rate(stats.inference_requests_per_second) if stats else "warming up"
    )

    trends.add_row(
        "CPU",
        cpu_history,
        current_cpu,
    )

    trends.add_row(
        "Infer/s",
        inference_history,
        current_inference,
    )

    identity = Table.grid(
        expand=True,
        padding=(0, 1),
    )

    identity.add_column(
        ratio=1,
    )

    identity.add_column(
        ratio=1,
    )

    identity.add_row(
        Panel(
            runtime_table,
            title="Runtime",
            border_style="cyan",
        ),
        Panel(
            model_table,
            title="Model",
            border_style="cyan",
        ),
    )

    traffic = Table.grid(
        expand=True,
        padding=(0, 1),
    )

    traffic.add_column(
        ratio=1,
    )

    traffic.add_column(
        ratio=1,
    )

    traffic.add_row(
        Panel(
            inference_table,
            title="Inference",
            border_style="cyan",
        ),
        Panel(
            mqtt_table,
            title="MQTT",
            border_style="cyan",
        ),
    )

    if poll_failures:
        footer_text = Text()

        footer_text.append(
            "Telemetry scrape degraded",
            style=("bold red" if poll_failures >= 3 else "bold yellow"),
        )

        if poll_error:
            footer_text.append(
                f" · {poll_error}",
                style="dim",
            )

    else:
        footer_text = Text(
            "Ctrl-C to quit",
            style="dim",
        )

    footer = Align.center(footer_text)

    return Group(
        Panel(
            header,
            title="[bold]EdgePulse Top[/bold]",
            border_style="bright_cyan",
        ),
        identity,
        Panel(
            resources,
            title="Resources",
            border_style="cyan",
        ),
        traffic,
        Panel(
            trends,
            title="Recent trend · 30 samples",
            border_style="cyan",
        ),
        Panel(
            latency_table,
            title="Inference latency",
            border_style="cyan",
        ),
        footer,
    )


class EdgePulseClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def snapshot(
        self,
    ) -> RuntimeSnapshot:
        health = _get_json(
            self.base_url,
            "/healthz",
            self.timeout,
        )

        readiness = _get_json(
            self.base_url,
            "/readyz",
            self.timeout,
        )

        model = _get_json(
            self.base_url,
            "/model/info",
            self.timeout,
        )

        metrics_text = _get_text(
            self.base_url,
            "/metrics",
            self.timeout,
        )

        execution_profile = model.get(
            "execution_profile",
            {},
        )

        return RuntimeSnapshot(
            health_status=str(
                health.get(
                    "status",
                    "unknown",
                )
            ),
            service=health.get("service"),
            readiness_status=str(
                readiness.get(
                    "status",
                    "unknown",
                )
            ),
            readiness_error=readiness.get("error"),
            model_name=model.get("model_name"),
            model_version=model.get("model_version"),
            model_backend=model.get("model_backend"),
            execution_profile=(execution_profile.get("name")),
            execution_profile_active=bool(
                execution_profile.get(
                    "active",
                    False,
                )
            ),
            metrics=parse_metrics(metrics_text),
        )


def run_live(
    client: EdgePulseClient,
    interval: float,
) -> int:
    previous: RuntimeSnapshot | None = None
    last_snapshot: RuntimeSnapshot | None = None
    last_stats: LiveStats | None = None

    poll_failures = 0

    history = DashboardHistory(
        size=30,
    )

    try:
        with Live(
            console=console,
            screen=console.is_terminal,
            auto_refresh=False,
        ) as live:
            while True:
                try:
                    current = client.snapshot()

                    stats = None

                    if previous is not None:
                        stats = derive_live_stats(
                            previous.metrics,
                            current.metrics,
                        )

                        history.add(stats)

                    previous = current
                    last_snapshot = current
                    last_stats = stats

                    poll_failures = 0

                    live.update(
                        build_dashboard(
                            current,
                            stats,
                            interval,
                            poll_failures=0,
                            history=history,
                        ),
                        refresh=True,
                    )

                except RuntimeError as exc:
                    poll_failures += 1

                    if last_snapshot is not None:
                        live.update(
                            build_dashboard(
                                last_snapshot,
                                last_stats,
                                interval,
                                poll_failures=(poll_failures),
                                poll_error=str(exc),
                                history=history,
                            ),
                            refresh=True,
                        )

                    else:
                        live.update(
                            Panel(
                                Align.center(
                                    Text.from_markup(
                                        "[bold red]"
                                        "Runtime unreachable"
                                        "[/]\n\n"
                                        f"{exc}\n\n"
                                        "[dim]"
                                        "waiting for first "
                                        "successful scrape"
                                        "[/]"
                                    ),
                                    vertical="middle",
                                ),
                                title="EdgePulse Top",
                                border_style="red",
                            ),
                            refresh=True,
                        )

                time.sleep(interval)

    except KeyboardInterrupt:
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Inspect the current operational state of an EdgePulse runtime."),
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=(f"EdgePulse runtime URL (default: {DEFAULT_BASE_URL})"),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help=(f"Live refresh interval in seconds (default: {DEFAULT_INTERVAL})."),
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--json",
        action="store_true",
        help=("Print one raw snapshot as JSON and exit."),
    )

    mode.add_argument(
        "--once",
        action="store_true",
        help=("Print one human-readable snapshot and exit."),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.interval <= 0:
        console.print("[bold red]edgepulse-top:[/] --interval must be greater than 0")
        return 2

    if args.timeout <= 0:
        console.print("[bold red]edgepulse-top:[/] --timeout must be greater than 0")
        return 2

    client = EdgePulseClient(
        args.base_url,
        timeout=args.timeout,
    )

    if not args.json and not args.once:
        return run_live(
            client,
            args.interval,
        )

    try:
        snapshot = client.snapshot()

    except RuntimeError as exc:
        console.print(f"[bold red]edgepulse-top:[/] {exc}")
        return 1

    if args.json:
        print(
            json.dumps(
                asdict(snapshot),
                indent=2,
            )
        )
        return 0

    print(render_snapshot(snapshot))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
