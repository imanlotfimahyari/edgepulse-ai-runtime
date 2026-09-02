# EdgePulse AI Runtime

EdgePulse AI Runtime is a compact, production-shaped edge-AI inference platform for industrial and IoT workloads.

It accepts device telemetry over HTTP or MQTT, runs local anomaly inference through a rule-based or ONNX Runtime backend, exposes operational metrics, and can be exercised locally with Docker Compose or deployed to Kubernetes with Helm.

The project is intentionally focused on **AI infrastructure and runtime operations**, not model research.

## What EdgePulse demonstrates

EdgePulse connects the layers that typically surround an edge inference workload:

```text
Simulated edge devices
        |
        +---- HTTP -----------------------------+
        |                                       |
        +---- MQTT / MQTTS ---> Mosquitto ------+
                                                |
                                                v
                                      EdgePulse AI Runtime
                                      - FastAPI API
                                      - MQTT consumer
                                      - configuration validation
                                      - rule-based / ONNX inference
                                      - readiness / liveness
                                      - Prometheus metrics
                                                |
                                                v
                                      Prometheus / Grafana
```

The repository demonstrates:

- HTTP and MQTT telemetry ingestion;
- local rule-based and ONNX Runtime inference;
- validated runtime configuration;
- health and dependency-aware readiness checks;
- resilient MQTT reconnect behavior;
- MQTT username/password authentication and TLS support;
- optional MQTT client certificates for mTLS-capable brokers;
- Prometheus-compatible metrics and a Grafana dashboard;
- Docker Compose integration testing across the real HTTP and MQTT paths;
- Helm-based Kubernetes deployment;
- Kubernetes Secret references for MQTT credentials and TLS material;
- local K3s validation with k3d;
- automated tests and coverage;
- dependency and IaC security checks;
- container SBOM generation and vulnerability scanning;
- GHCR image publishing and keyless Cosign signing.

## Current version

Current project and chart version: **`0.9.0`**.

The Helm chart metadata and published runtime image use the same application version:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

## Runtime endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /healthz` | Liveness: confirms that the process is running. |
| `GET /readyz` | Readiness: confirms that the runtime can serve inference; when MQTT is enabled, MQTT connectivity is also required. |
| `GET /model/info` | Returns model and backend metadata. |
| `POST /infer` | Runs inference for HTTP telemetry. |
| `GET /metrics` | Exposes Prometheus-compatible runtime metrics. |

## Inference backends

| Backend | Purpose |
| --- | --- |
| `rule-based` | Lightweight deterministic anomaly scoring for runtime/platform testing. |
| `onnx` | ONNX Runtime inference using the packaged anomaly-scoring model. |

Select the backend with:

```bash
MODEL_BACKEND=rule-based
# or
MODEL_BACKEND=onnx
```

When ONNX mode is selected, the runtime loads the configured model during application startup. A model initialization failure makes `/readyz` report not ready.

## Quick start: secured Docker Compose stack

The Compose environment uses an authenticated TLS-enabled Mosquitto broker. Test PKI material and the local password database are generated into an ephemeral Docker volume; private keys are not committed to the repository.

Clean any previous local stack and security volume:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  down -v --remove-orphans
```

Start the broker and runtime:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  up -d --build mqtt edgepulse-runtime
```

Check the runtime:

```bash
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/readyz | jq
curl -s http://localhost:8080/model/info | jq
curl -s http://localhost:8080/metrics | grep edgepulse
```

Run the end-to-end test as a one-off Compose service:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  run --rm --no-deps --build e2e
```

Expected final output:

```text
EdgePulse Compose E2E test passed
```

The E2E test validates the assembled system rather than isolated functions:

```text
E2E service
   |
   +--> HTTP --> EdgePulse Runtime --> inference --> metrics
   |
   +--> MQTTS + auth --> Mosquitto --> Runtime MQTT consumer
                                      --> inference --> metrics
```

Stop and remove the local stack when finished:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  down -v --remove-orphans
```

## HTTP simulator example

With the runtime available on `localhost:8080`:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

The repository also contains temperature, power-meter, and camera-like simulators.

The current generic simulator CLI is most convenient for HTTP and plaintext MQTT development. The secured Compose MQTT path is validated through the dedicated E2E service, which injects its TLS trust and test credentials through environment variables.

## Observability

Useful metrics include:

```text
edgepulse_device_messages_total
edgepulse_inference_requests_total
edgepulse_inference_latency_seconds
edgepulse_inference_errors_total
edgepulse_mqtt_connected
edgepulse_mqtt_messages_total
edgepulse_mqtt_errors_total
edgepulse_model_info
```

Example checks:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_connected
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
curl -s http://localhost:8080/metrics | grep 'model_backend="onnx"'
```

A Grafana dashboard is available at:

```text
dashboards/grafana/edgepulse-overview.json
```

See [docs/observability.md](docs/observability.md) for PromQL examples and [docs/servicemonitor.md](docs/servicemonitor.md) for Prometheus Operator integration.

## Kubernetes and Helm

The Helm chart is located at:

```text
charts/edgepulse-runtime
```

Validate it with:

```bash
helm lint charts/edgepulse-runtime
helm template edgepulse-runtime charts/edgepulse-runtime > /tmp/edgepulse-rendered.yaml
```

Install the default chart:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace
```

The chart can deploy the bundled Mosquitto broker and supports secure MQTT configuration through **existing Kubernetes Secrets**. It does not generate production credentials or certificates.

This allows the operational ownership to remain clean:

```text
cert-manager / external PKI  ---> TLS Secret --------+
External Secrets / operator  ---> credential Secret -+--> Helm-mounted configuration
                                                     |
                                                     +--> EdgePulse runtime
                                                     +--> Mosquitto
```

See [charts/edgepulse-runtime/README.md](charts/edgepulse-runtime/README.md) for values and secure MQTT examples, and [docs/k3d-k3s-local.md](docs/k3d-k3s-local.md) for local Kubernetes validation.

## CI and security validation

The repository uses GitHub Actions to validate:

- pre-commit hooks;
- Python compilation;
- Ruff lint and formatting;
- pytest runtime tests with coverage;
- Helm lint and template rendering;
- Docker image builds;
- Python dependency audits;
- Checkov Helm/Dockerfile scanning;
- secured Docker Compose E2E validation.

Separate workflows provide:

- SPDX SBOM generation;
- container vulnerability scanning;
- GHCR image publishing;
- keyless Cosign image signing.

See:

- [docs/security.md](docs/security.md)
- [docs/container-security.md](docs/container-security.md)
- [docs/release.md](docs/release.md)
- [docs/image-signing.md](docs/image-signing.md)

## Repository structure

```text
.
├── charts/
│   └── edgepulse-runtime/        # Helm chart and deployment values
├── dashboards/
│   └── grafana/                  # Importable Grafana dashboard
├── deploy/
│   └── docker-compose/           # Secured local integration environment
├── docs/                         # Architecture, operations, security, release guides
├── runtime/                      # FastAPI runtime, inference backends, tests
├── scripts/                      # Model utilities and Compose E2E runner
└── simulators/                   # Simulated edge-device producers
```

## Documentation map

| Document | Use it for |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, data paths, readiness, security boundaries. |
| [Demo walkthrough](docs/demo-walkthrough.md) | A concise technical demonstration of the project. |
| [Local k3d/K3s](docs/k3d-k3s-local.md) | Kubernetes validation on a workstation. |
| [Observability](docs/observability.md) | Metrics, PromQL, Grafana, MQTT connectivity. |
| [ServiceMonitor](docs/servicemonitor.md) | Prometheus Operator integration. |
| [Security](docs/security.md) | Runtime, MQTT, Kubernetes, and CI security posture. |
| [Container security](docs/container-security.md) | SBOM and vulnerability scan workflow. |
| [Release](docs/release.md) | Version-tagged GHCR publication workflow. |
| [Image signing](docs/image-signing.md) | Keyless Cosign signing and verification. |
| [Troubleshooting](docs/troubleshooting.md) | Runtime, MQTT, TLS, Compose, and Kubernetes diagnostics. |
| [Roadmap](docs/project-roadmap.md) | Current state and next production-oriented increments. |

## Scope

EdgePulse is deliberately small enough to understand end to end. Its purpose is to demonstrate the operational path of an AI workload—from telemetry ingestion through inference, deployment, observability, security, and release—without hiding the core concepts behind a large framework.

It is not intended to be a complete device-management platform, training platform, or production MQTT PKI system.

## License

Apache License 2.0. See [LICENSE](LICENSE).
