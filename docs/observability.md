# Observability

EdgePulse AI Runtime exposes Prometheus-compatible metrics through:

```text
GET /metrics
```

The metrics are designed to make the runtime observable by device type, ingestion mode, prediction, and model backend.

## Main metrics

| Metric | Purpose |
|---|---|
| `edgepulse_device_messages_total` | Count of received device messages |
| `edgepulse_inference_requests_total` | Count of inference requests by prediction, backend, and ingestion mode |
| `edgepulse_inference_latency_seconds` | Inference latency histogram |
| `edgepulse_inference_errors_total` | Inference error count |
| `edgepulse_mqtt_messages_total` | MQTT message count by topic and device type |
| `edgepulse_mqtt_errors_total` | MQTT consumer error count |
| `edgepulse_model_info` | Model metadata exposed as labels |

## Important labels

| Label | Meaning |
|---|---|
| `device_type` | Simulated device type |
| `ingestion` | `http` or `mqtt` |
| `prediction` | `normal` or `anomaly` |
| `model_backend` | `rule-based` or `onnx` |
| `topic` | MQTT topic |

## Docker Compose scrape example

When Prometheus runs in the same Docker Compose network, scrape the runtime service name:

```yaml
scrape_configs:
  - job_name: edgepulse-runtime
    metrics_path: /metrics
    static_configs:
      - targets:
          - edgepulse-runtime:8080
```

When Prometheus runs directly on the host, scrape localhost:

```yaml
scrape_configs:
  - job_name: edgepulse-runtime-local
    metrics_path: /metrics
    static_configs:
      - targets:
          - localhost:8080
```

## Kubernetes scrape example

When deployed with Helm into the `edgepulse` namespace, the runtime Service is:

```text
edgepulse-runtime.edgepulse.svc.cluster.local:8080
```

Example static Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: edgepulse-runtime-kubernetes
    metrics_path: /metrics
    static_configs:
      - targets:
          - edgepulse-runtime.edgepulse.svc.cluster.local:8080
```

## Useful PromQL queries

Device message rate by type and ingestion:

```promql
sum(rate(edgepulse_device_messages_total[$__rate_interval])) by (device_type, ingestion)
```

Inference rate by prediction, backend, and ingestion:

```promql
sum(rate(edgepulse_inference_requests_total[$__rate_interval])) by (prediction, model_backend, ingestion)
```

MQTT message rate by device type and topic:

```promql
sum(rate(edgepulse_mqtt_messages_total[$__rate_interval])) by (device_type, topic)
```

P95 inference latency:

```promql
histogram_quantile(
  0.95,
  sum(rate(edgepulse_inference_latency_seconds_bucket[$__rate_interval])) by (le, device_type, ingestion, model_backend)
)
```

Runtime inference error rate:

```promql
sum(rate(edgepulse_inference_errors_total[$__rate_interval])) by (device_type, ingestion, model_backend)
```

MQTT consumer error rate:

```promql
sum(rate(edgepulse_mqtt_errors_total[$__rate_interval])) by (topic)
```

Current model backend metadata:

```promql
edgepulse_model_info
```

## Grafana dashboard

A ready-to-import Grafana dashboard is available at:

```text
dashboards/grafana/edgepulse-overview.json
```

The dashboard includes panels for:

- device message rate;
- inference rate;
- inference latency;
- MQTT message rate;
- runtime and MQTT error rate;
- current model backend metadata.

## Manual Grafana import

In Grafana:

1. Open Dashboards.
2. Select New / Import.
3. Upload `dashboards/grafana/edgepulse-overview.json`.
4. Select the Prometheus data source.
5. Import the dashboard.
