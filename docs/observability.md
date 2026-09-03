# Observability

EdgePulse exposes Prometheus-compatible metrics at:

```text
GET /metrics
```

The metrics cover workload behavior, inference performance, and MQTT dependency state.

## Metric inventory

| Metric | Type / purpose |
| --- | --- |
| `edgepulse_device_messages_total` | Device messages by device type and ingestion path. |
| `edgepulse_inference_requests_total` | Inference requests by device type, prediction, backend, and ingestion. |
| `edgepulse_inference_latency_seconds` | Inference latency histogram. |
| `edgepulse_inference_errors_total` | Inference processing errors. |
| `edgepulse_mqtt_connected` | Gauge: `1` while the runtime MQTT client is connected, otherwise `0`. |
| `edgepulse_mqtt_messages_total` | MQTT messages by topic and device type. |
| `edgepulse_mqtt_errors_total` | MQTT message-processing errors by topic. |
| `edgepulse_model_info` | Current model metadata represented as labels. |

## Important labels

| Label | Meaning |
| --- | --- |
| `device_type` | Device/simulator type. |
| `ingestion` | `http` or `mqtt`. |
| `prediction` | Inference result, for example `normal` or `anomaly`. |
| `model_backend` | `rule-based` or `onnx`. |
| `topic` | MQTT topic. |

These labels make it possible to compare transport behavior and model behavior without maintaining separate metric families for each path.

## Quick checks

MQTT connection state:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_connected
```

HTTP vs MQTT inference:

```bash
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
```

Backend-specific metrics:

```bash
curl -s http://localhost:8080/metrics | grep 'model_backend="rule-based"'
curl -s http://localhost:8080/metrics | grep 'model_backend="onnx"'
```

## Prometheus scrape examples

### Same Docker network

```yaml
scrape_configs:
  - job_name: edgepulse-runtime
    metrics_path: /metrics
    static_configs:
      - targets:
          - edgepulse-runtime:8080
```

### Prometheus on the host

```yaml
scrape_configs:
  - job_name: edgepulse-runtime-local
    metrics_path: /metrics
    static_configs:
      - targets:
          - localhost:8080
```

### Kubernetes

For a release named `edgepulse-runtime` in namespace `edgepulse`:

```yaml
scrape_configs:
  - job_name: edgepulse-runtime-kubernetes
    metrics_path: /metrics
    static_configs:
      - targets:
          - edgepulse-runtime.edgepulse.svc.cluster.local:8080
```

For Prometheus Operator, prefer the chart's optional `ServiceMonitor`; see `docs/servicemonitor.md`.

## Useful PromQL

Device traffic rate:

```promql
sum(rate(edgepulse_device_messages_total[$__rate_interval]))
  by (device_type, ingestion)
```

Inference rate:

```promql
sum(rate(edgepulse_inference_requests_total[$__rate_interval]))
  by (prediction, model_backend, ingestion)
```

MQTT message rate:

```promql
sum(rate(edgepulse_mqtt_messages_total[$__rate_interval]))
  by (device_type, topic)
```

P95 inference latency:

```promql
histogram_quantile(
  0.95,
  sum(rate(edgepulse_inference_latency_seconds_bucket[$__rate_interval]))
    by (le, device_type, ingestion, model_backend)
)
```

Inference error rate:

```promql
sum(rate(edgepulse_inference_errors_total[$__rate_interval]))
  by (device_type, ingestion, model_backend)
```

MQTT processing error rate:

```promql
sum(rate(edgepulse_mqtt_errors_total[$__rate_interval])) by (topic)
```

MQTT disconnected condition:

```promql
edgepulse_mqtt_connected == 0
```

Current model metadata:

```promql
edgepulse_model_info
```

## Readiness and metrics

`/readyz` and `edgepulse_mqtt_connected` complement each other:

```text
/readyz
  -> Kubernetes/load-balancer decision: can this instance serve now?

edgepulse_mqtt_connected
  -> monitoring signal: is the MQTT dependency currently connected?
```

When MQTT is enabled and disconnected, readiness returns a non-ready response while the process remains live.

## Grafana dashboard

An importable dashboard is available at:

```text
dashboards/grafana/edgepulse-overview.json
```

It includes views for device traffic, inference rates, latency, MQTT traffic/errors, and current model metadata.

Import it by uploading the JSON in Grafana and selecting the target Prometheus data source.

## Edge resource observability

EdgePulse exposes cgroup-aware resource metrics when running on Linux cgroup v2.

These metrics describe the resource budget assigned to the runtime container rather
than the resources of the entire host.

### Resource metrics

| Metric | Description |
| --- | --- |
| `edgepulse_resource_cgroup_v2_available` | Whether cgroup v2 metrics are available |
| `edgepulse_resource_memory_current_bytes` | Current cgroup memory usage |
| `edgepulse_resource_memory_peak_bytes` | Peak cgroup memory usage |
| `edgepulse_resource_memory_limited` | Whether a finite memory limit is configured |
| `edgepulse_resource_memory_limit_bytes` | Configured memory limit |
| `edgepulse_resource_memory_headroom_bytes` | Remaining memory before the limit |
| `edgepulse_resource_memory_utilization_ratio` | Memory usage divided by memory limit |
| `edgepulse_resource_cpu_limited` | Whether a finite CPU quota is configured |
| `edgepulse_resource_cpu_limit_cores` | CPU quota expressed as CPU cores |
| `edgepulse_inference_in_progress` | Number of currently executing inference operations |
| `edgepulse_model_artifact_size_bytes` | Size of the configured model artifact |

The Python Prometheus client also exports process-level metrics such as
`process_resident_memory_bytes` and `process_cpu_seconds_total`.

The process and cgroup metrics answer different questions:

- process metrics describe the Python runtime process;
- cgroup metrics describe the resource consumption and limits of the container.

For example, memory utilization can be queried with:

```promql
edgepulse_resource_memory_utilization_ratio
```

CPU consumption can be compared with the configured CPU budget using:

```promql
rate(process_cpu_seconds_total[$__rate_interval])
```

and:

```promql
edgepulse_resource_cpu_limit_cores
```

The Grafana dashboard includes an Edge Resource Efficiency section showing memory utilization, memory headroom, CPU budget, model size, memory usage versus limit, CPU usage versus limit, and inference concurrency.

## Next observability increments

Useful future additions include:

- alert rules for prolonged MQTT disconnection;
- inference error-rate alerts;
- latency SLO panels;
- OpenTelemetry traces for ingestion-to-inference flow;
- richer broker metrics when a production MQTT observability path is introduced.
