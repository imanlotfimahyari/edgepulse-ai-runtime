# Architecture

EdgePulse AI Runtime demonstrates the infrastructure and runtime layer around an edge-AI inference workload.

The design intentionally keeps the model simple so the operational path remains visible.

## System view

```text
                    +-------------------------+
                    | Simulated edge devices  |
                    +-----------+-------------+
                                |
                    +-----------+-----------+
                    |                       |
                 HTTP                    MQTT/MQTTS
                    |                       |
                    v                       v
           POST /infer               Mosquitto broker
                    |                       |
                    |                       | edge/devices/+/telemetry
                    |                       v
                    |               MQTT consumer thread
                    |                       |
                    +-----------+-----------+
                                |
                                v
                    process_inference_request()
                                |
                    +-----------+-----------+
                    |                       |
               rule-based                ONNX Runtime
                    |                       |
                    +-----------+-----------+
                                |
                                v
                         Prometheus metrics
                                |
                                v
                         Prometheus/Grafana
```

## Components

### FastAPI runtime

The runtime exposes:

| Endpoint | Responsibility |
| --- | --- |
| `GET /healthz` | Process liveness. |
| `GET /readyz` | Dependency-aware readiness. |
| `GET /model/info` | Model/backend metadata. |
| `POST /infer` | HTTP telemetry ingestion and inference. |
| `GET /metrics` | Prometheus-compatible metrics. |

FastAPI startup uses the application lifespan to initialize runtime state. When the ONNX backend is selected, the ONNX session is loaded during startup rather than lazily on the first request.

### Configuration layer

Runtime settings are validated through `pydantic-settings`.

Important configuration domains include:

```text
model backend and model path
anomaly threshold
MQTT host / port / topic
MQTT authentication
MQTT TLS trust
optional MQTT client certificate/key
```

Invalid combinations fail configuration validation early. Examples include a password without a username, incomplete client-certificate configuration, or TLS files configured while TLS is disabled.

### HTTP ingestion

```text
simulator / client
       |
       | POST /infer
       v
FastAPI request validation
       |
       v
shared inference service
       |
       v
metrics + response
```

HTTP and MQTT do not implement separate inference logic. Both converge on the same service layer.

### MQTT ingestion

```text
device / publisher
       |
       | publish
       v
MQTT broker
       |
       | subscribed topic
       v
runtime MQTT consumer
       |
       v
schema validation
       |
       v
shared inference service
       |
       v
metrics
```

The runtime subscribes to:

```text
edge/devices/+/telemetry
```

The MQTT client uses asynchronous connection plus retry behavior and tracks connection state with a thread-safe event.

### MQTT security

The runtime supports:

- username/password authentication;
- TLS server verification through a CA file;
- optional client certificate and key for mTLS-capable brokers.

Security configuration is applied to the Paho client before connection establishment.

Local Docker Compose testing uses generated, ephemeral test PKI material and separate runtime/simulator identities. Kubernetes deployment references existing Secrets rather than generating credentials in the Helm chart.

## Inference backends

### Rule-based

The rule-based backend provides deterministic anomaly scoring without a model-serving dependency. It is useful for validating ingestion, deployment, reliability, and observability behavior.

### ONNX Runtime

The ONNX backend loads the packaged model artifact and executes inference locally.

```text
MODEL_BACKEND=onnx
MODEL_PATH=/app/models/anomaly_score.onnx
```

The backend is intentionally lightweight; the project focus is model runtime infrastructure rather than model training.

## Liveness and readiness

Liveness and readiness have different semantics.

```text
/healthz
   |
   +--> process is alive

/readyz
   |
   +--> runtime initialization succeeded
   +--> configured inference backend is usable
   +--> MQTT is connected when MQTT is enabled
```

A broker outage therefore does not make the process dead, but it does make an MQTT-dependent instance not ready.

## Observability path

Metrics record both workload behavior and runtime dependencies.

Important dimensions include:

```text
device_type
prediction
model_backend
ingestion
topic
```

The `ingestion` dimension distinguishes:

```text
ingestion="http"
ingestion="mqtt"
```

MQTT connection state is also exposed as a gauge so the broker dependency can be monitored independently from inference counters.

See `docs/observability.md` for the current metric set and PromQL examples.

## Deployment models

### Docker Compose

The Compose environment is an integration environment, not just a process launcher.

```text
security init service
       |
       +--> ephemeral CA/server cert/password DB
                         |
                         v
                  Mosquitto :8883
                    /          \
                   / TLS+auth   \
                  v              v
         EdgePulse runtime      E2E service
```

The E2E service runs inside the same Compose network and validates real HTTP and MQTT traffic.

### Kubernetes / Helm

```text
existing Secrets
   |
   +--> broker password file
   +--> broker TLS cert/key
   +--> runtime username/password
   +--> runtime CA / optional client cert
   |
   v
Helm-rendered Deployments
   |
   +--> EdgePulse Runtime
   +--> optional Mosquitto broker
```

The chart keeps secret issuance outside its scope so production clusters can use cert-manager, External Secrets, cloud secret managers, or another platform-standard mechanism.

## Current boundaries

Implemented:

- HTTP and MQTT ingestion;
- rule-based and ONNX backends;
- configuration validation;
- dependency-aware readiness;
- MQTT reconnect and connection metrics;
- MQTT authentication and TLS client behavior;
- Prometheus metrics and Grafana dashboard;
- Compose E2E validation;
- Helm/Kubernetes deployment;
- secure Secret wiring;
- CI, security scanning, SBOM, and signed image release.

Not implemented as a full production subsystem:

- device registry and per-device authorization;
- broker ACL automation;
- certificate issuance/rotation orchestration;
- model registry integration;
- distributed MQTT consumer scaling strategy;
- telemetry persistence;
- edge-fleet management.
