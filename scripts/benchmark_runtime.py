from __future__ import annotations

import argparse
import http.client
import json
import math
import statistics
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass
class WorkerResult:
    requests: int
    errors: int
    client_latencies_ms: list[float]
    inference_latencies_ms: list[float]


@dataclass
class ResourceSamples:
    memory_bytes: list[float]


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None

    values = sorted(values)
    index = max(0, math.ceil(fraction * len(values)) - 1)

    return values[index]


def get_json(base_url: str, path: str, timeout: float) -> dict:
    with urllib.request.urlopen(
        f"{base_url}{path}",
        timeout=timeout,
    ) as response:
        return json.loads(response.read())


def get_metrics(base_url: str, timeout: float) -> dict[str, float]:
    with urllib.request.urlopen(
        f"{base_url}/metrics",
        timeout=timeout,
    ) as response:
        text = response.read().decode()

    metrics: dict[str, float] = {}

    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue

        name, separator, raw_value = line.partition(" ")

        # This benchmark currently consumes only metrics without labels.
        if not separator or "{" in name:
            continue

        try:
            metrics[name] = float(raw_value)
        except ValueError:
            continue

    return metrics


def create_connection(base_url: str, timeout: float):
    parsed = urlsplit(base_url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base URL must use http or https")

    if parsed.hostname is None:
        raise ValueError("base URL must contain a hostname")

    connection_class = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )

    return connection_class(
        parsed.hostname,
        port=parsed.port,
        timeout=timeout,
    )


def run_worker(
    base_url: str,
    duration: float,
    timeout: float,
    payload: bytes,
    start_barrier: threading.Barrier,
) -> WorkerResult:
    result = WorkerResult(
        requests=0,
        errors=0,
        client_latencies_ms=[],
        inference_latencies_ms=[],
    )

    connection = create_connection(base_url, timeout)

    start_barrier.wait()
    deadline = time.perf_counter() + duration

    try:
        while time.perf_counter() < deadline:
            started = time.perf_counter()

            try:
                connection.request(
                    "POST",
                    "/infer",
                    body=payload,
                    headers={"Content-Type": "application/json"},
                )

                response = connection.getresponse()
                body = response.read()

                client_latency_ms = (time.perf_counter() - started) * 1000

                if response.status != 200:
                    result.errors += 1
                    continue

                response_body = json.loads(body)

                result.requests += 1
                result.client_latencies_ms.append(client_latency_ms)

                inference_latency = response_body.get("latency_ms")

                if isinstance(inference_latency, (int, float)):
                    result.inference_latencies_ms.append(float(inference_latency))

            except (
                ConnectionError,
                TimeoutError,
                OSError,
                http.client.HTTPException,
                json.JSONDecodeError,
            ):
                result.errors += 1

                connection.close()
                connection = create_connection(
                    base_url,
                    timeout,
                )

    finally:
        connection.close()

    return result


def run_load(
    base_url: str,
    duration: float,
    concurrency: int,
    timeout: float,
    payload: bytes,
) -> tuple[float, list[WorkerResult]]:
    barrier = threading.Barrier(concurrency + 1)

    results: list[WorkerResult | None] = [None] * concurrency
    threads: list[threading.Thread] = []

    def worker(index: int) -> None:
        results[index] = run_worker(
            base_url,
            duration,
            timeout,
            payload,
            barrier,
        )

    for index in range(concurrency):
        thread = threading.Thread(
            target=worker,
            args=(index,),
        )
        thread.start()
        threads.append(thread)

    barrier.wait()
    started = time.perf_counter()

    for thread in threads:
        thread.join()

    elapsed = time.perf_counter() - started

    return elapsed, [result for result in results if result is not None]


def sample_resources(
    base_url: str,
    timeout: float,
    stop_event: threading.Event,
    samples: ResourceSamples,
    interval: float = 0.2,
) -> None:
    while not stop_event.is_set():
        try:
            metrics = get_metrics(base_url, timeout)

            memory = metrics.get("edgepulse_resource_memory_current_bytes")

            if memory is not None:
                samples.memory_bytes.append(memory)

        except (OSError, TimeoutError):
            pass

        stop_event.wait(interval)


def format_ms(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:.3f} ms"


def format_mib(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value / 1024 / 1024:.1f} MiB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark an EdgePulse runtime.")

    parser.add_argument(
        "--base-url",
        default="http://host.docker.internal:8080",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
    )
    parser.add_argument(
        "--warmup",
        type=float,
        default=2.0,
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
    )
    parser.add_argument(
        "--output",
        type=Path,
    )

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.warmup < 0:
        parser.error("--warmup must be zero or greater")

    if args.concurrency <= 0:
        parser.error("--concurrency must be greater than zero")

    base_url = args.base_url.rstrip("/")

    health = get_json(
        base_url,
        "/healthz",
        args.timeout,
    )

    readiness = get_json(
        base_url,
        "/readyz",
        args.timeout,
    )

    model = get_json(
        base_url,
        "/model/info",
        args.timeout,
    )

    if readiness.get("status") != "ready":
        raise RuntimeError(f"runtime is not ready: {readiness}")

    payload = json.dumps(
        {
            "device_id": "benchmark-001",
            "device_type": "vibration_sensor",
            "payload_type": "vibration",
            "features": [
                0.12,
                0.14,
                0.19,
                0.25,
                0.22,
            ],
        }
    ).encode()

    # Warm the HTTP and inference path before collecting measurements.
    if args.warmup > 0:
        run_load(
            base_url,
            args.warmup,
            args.concurrency,
            args.timeout,
            payload,
        )

    metrics_before = get_metrics(
        base_url,
        args.timeout,
    )

    resource_samples = ResourceSamples(
        memory_bytes=[],
    )

    sampler_stop = threading.Event()

    sampler = threading.Thread(
        target=sample_resources,
        args=(
            base_url,
            args.timeout,
            sampler_stop,
            resource_samples,
        ),
        daemon=True,
    )

    sampler.start()

    try:
        elapsed, worker_results = run_load(
            base_url,
            args.duration,
            args.concurrency,
            args.timeout,
            payload,
        )
    finally:
        sampler_stop.set()
        sampler.join()

    metrics_after = get_metrics(
        base_url,
        args.timeout,
    )

    successful_requests = sum(result.requests for result in worker_results)

    errors = sum(result.errors for result in worker_results)

    client_latencies = [
        latency for result in worker_results for latency in result.client_latencies_ms
    ]

    inference_latencies = [
        latency
        for result in worker_results
        for latency in result.inference_latencies_ms
    ]

    cpu_before = metrics_before.get("process_cpu_seconds_total")

    cpu_after = metrics_after.get("process_cpu_seconds_total")

    cpu_seconds = None

    if cpu_before is not None and cpu_after is not None:
        cpu_seconds = max(
            0.0,
            cpu_after - cpu_before,
        )

    average_cpu_cores = None

    if cpu_seconds is not None and elapsed > 0:
        average_cpu_cores = cpu_seconds / elapsed

    cpu_limit = metrics_after.get("edgepulse_resource_cpu_limit_cores")

    cpu_budget_utilization = None

    if average_cpu_cores is not None and cpu_limit is not None and cpu_limit > 0:
        cpu_budget_utilization = average_cpu_cores / cpu_limit

    inferences_per_cpu_second = None

    if cpu_seconds is not None and cpu_seconds > 0:
        inferences_per_cpu_second = successful_requests / cpu_seconds

    benchmark_memory_average = (
        statistics.fmean(resource_samples.memory_bytes)
        if resource_samples.memory_bytes
        else None
    )

    benchmark_memory_max = (
        max(resource_samples.memory_bytes) if resource_samples.memory_bytes else None
    )

    result = {
        "runtime": {
            "service": health.get("service"),
            "model_name": model.get("model_name"),
            "model_version": model.get("model_version"),
            "model_backend": model.get("model_backend"),
            "execution_profile": model.get("execution_profile"),
        },
        "workload": {
            "duration_seconds": elapsed,
            "warmup_seconds": args.warmup,
            "concurrency": args.concurrency,
            "requests": successful_requests,
            "errors": errors,
            "throughput_requests_per_second": (successful_requests / elapsed),
        },
        "client_latency_ms": {
            "p50": percentile(
                client_latencies,
                0.50,
            ),
            "p95": percentile(
                client_latencies,
                0.95,
            ),
            "p99": percentile(
                client_latencies,
                0.99,
            ),
            "mean": (statistics.fmean(client_latencies) if client_latencies else None),
        },
        "inference_latency_ms": {
            "p50": percentile(
                inference_latencies,
                0.50,
            ),
            "p95": percentile(
                inference_latencies,
                0.95,
            ),
            "p99": percentile(
                inference_latencies,
                0.99,
            ),
            "mean": (
                statistics.fmean(inference_latencies) if inference_latencies else None
            ),
        },
        "resources": {
            "cpu_seconds": cpu_seconds,
            "average_cpu_cores": average_cpu_cores,
            "cpu_limit_cores": cpu_limit,
            "cpu_budget_utilization_ratio": (cpu_budget_utilization),
            "memory_average_bytes": (benchmark_memory_average),
            "memory_max_observed_bytes": (benchmark_memory_max),
            "memory_current_bytes": (
                metrics_after.get("edgepulse_resource_memory_current_bytes")
            ),
            "memory_peak_bytes": (
                metrics_after.get("edgepulse_resource_memory_peak_bytes")
            ),
            "memory_limit_bytes": (
                metrics_after.get("edgepulse_resource_memory_limit_bytes")
            ),
            "memory_headroom_bytes": (
                metrics_after.get("edgepulse_resource_memory_headroom_bytes")
            ),
        },
        "efficiency": {
            "inferences_per_cpu_second": (inferences_per_cpu_second),
        },
    }

    print("EdgePulse Benchmark")
    print("=" * 48)

    print(f"Backend             {model.get('model_backend')}")
    execution_profile = model.get(
        "execution_profile",
        {},
    )

    print(f"Profile             {execution_profile.get('name', 'n/a')}")
    print(f"Duration            {elapsed:.2f} s")
    print(f"Concurrency         {args.concurrency}")
    print(f"Requests            {successful_requests}")
    print(f"Errors              {errors}")
    print(f"Throughput          {successful_requests / elapsed:.2f} req/s")

    print()
    print("Client latency")
    print(f"  p50               {format_ms(result['client_latency_ms']['p50'])}")
    print(f"  p95               {format_ms(result['client_latency_ms']['p95'])}")
    print(f"  p99               {format_ms(result['client_latency_ms']['p99'])}")

    print()
    print("Inference latency")
    print(f"  p50               {format_ms(result['inference_latency_ms']['p50'])}")
    print(f"  p95               {format_ms(result['inference_latency_ms']['p95'])}")
    print(f"  p99               {format_ms(result['inference_latency_ms']['p99'])}")

    print()
    print("Resources")

    if average_cpu_cores is None:
        print("  Average CPU       n/a")
    else:
        print(f"  Average CPU       {average_cpu_cores:.3f} cores")

    if cpu_limit is None:
        print("  CPU budget        unlimited")
    else:
        print(f"  CPU budget        {cpu_limit:.3f} cores")

    if cpu_budget_utilization is None:
        print("  CPU utilization   n/a")
    else:
        print(f"  CPU utilization   {cpu_budget_utilization * 100:.1f}%")

    print(f"  Memory average    {format_mib(benchmark_memory_average)}")
    print(f"  Memory max        {format_mib(benchmark_memory_max)}")
    print(f"  Cgroup peak       {format_mib(result['resources']['memory_peak_bytes'])}")
    print(
        f"  Memory budget     {format_mib(result['resources']['memory_limit_bytes'])}"
    )
    print(
        f"  Memory headroom   "
        f"{format_mib(result['resources']['memory_headroom_bytes'])}"
    )

    print()
    print("Efficiency")

    if inferences_per_cpu_second is None:
        print("  Infer / CPU-s     n/a")
    else:
        print(f"  Infer / CPU-s     {inferences_per_cpu_second:.2f}")

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            json.dumps(
                result,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        print()
        print(f"Result written to   {args.output}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
