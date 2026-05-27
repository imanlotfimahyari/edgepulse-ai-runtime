# EdgePulse AI Runtime Architecture

EdgePulse AI Runtime demonstrates the platform layer around edge-AI workloads.

The system supports two ingestion modes:

```text
HTTP:
simulated device -> POST /infer -> runtime -> inference -> metrics

MQTT:
simulated device -> Mosquitto -> runtime MQTT consumer -> inference -> metrics
```

## Components

### EdgePulse Runtime

The runtime is a FastAPI service that exposes:

- `GET /healthz`
- `GET /readyz`
- `GET /model/info`
- `POST /infer`
- `GET /metrics`

It receives telemetry, validates the payload, runs anomaly/inference logic, and exposes Prometheus-compatible metrics.

### HTTP Ingestion

HTTP ingestion is useful for direct API-style integration.

```text
simulated device
      |
      | POST /infer
      v
EdgePulse Runtime
      |
      v
shared inference service
      |
      v
Prometheus metrics
```

### MQTT Ingestion

MQTT ingestion is closer to real edge and IoT environments.

```text
simulated device
      |
      | publish telemetry
      v
Mosquitto MQTT broker
      |
      | edge/devices/+/telemetry
      v
EdgePulse Runtime MQTT consumer
      |
      v
shared inference service
      |
      v
Prometheus metrics
```

The runtime subscribes to:

```text
edge/devices/+/telemetry
```

### Simulated Devices

The project currently includes four simulated device types:

- vibration sensor;
- temperature sensor;
- power meter;
- camera-like device.

Each simulator can send telemetry through either HTTP or MQTT.

### Shared Inference Path

Both HTTP and MQTT messages are processed through the same shared inference path.

```text
HTTP /infer -------------+
                         |
                         v
                  process_inference_request()
                         ^
                         |
MQTT consumer -----------+
```

This keeps runtime behavior consistent across ingestion modes.

### Metrics

Metrics include:

- inference requests by device type, prediction, backend, and ingestion mode;
- inference latency by device type, backend, and ingestion mode;
- device messages by device type and ingestion mode;
- MQTT messages by topic and device type;
- model metadata.

Important metric labels include:

```text
device_type
prediction
model_backend
ingestion
topic
```

The `ingestion` label distinguishes HTTP traffic from MQTT traffic:

```text
ingestion="http"
ingestion="mqtt"
```

## Current Scope

The current version focuses on local edge-runtime behavior:

- Docker Compose deployment;
- FastAPI runtime;
- Mosquitto broker;
- simulated devices;
- rule-based anomaly detection;
- Prometheus-compatible metrics.

Kubernetes, Helm, ONNX Runtime, Grafana dashboards, and CI/CD are planned next.
