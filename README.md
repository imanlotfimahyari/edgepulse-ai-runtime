# EdgePulse AI Runtime

EdgePulse AI Runtime is a compact, production-shaped edge-AI inference platform for industrial and IoT workloads.

It accepts device telemetry over HTTP or MQTT, runs local anomaly inference through a rule-based or ONNX Runtime backend, exposes operational and resource metrics, and can be exercised locally with Docker Compose or deployed to Kubernetes with Helm.

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
                                      - FP32 / INT8 model artifacts
                                      - ONNX execution profiles
                                      - readiness / liveness
                                      - cgroup resource awareness
                                      - Prometheus metrics
                                                |
                    +---------------------------+-------------------------+
                    |                           |                         |
                    v                           v                         v
              edgepulse-top             Prometheus / Grafana       benchmark tooling
              node-local state          history / dashboards       controlled load
```

The repository demonstrates:

* HTTP and MQTT telemetry ingestion;
* local rule-based and ONNX Runtime inference;
* deterministic generation of a weight-bearing FP32 ONNX model;
* dynamic INT8 quantization for CPU inference;
* numerical comparison of FP32 and INT8 model variants;
* model artifact manifests with checksum verification;
* explicit model-path and manifest-path selection;
* runtime detection of model/manifest selection mismatches;
* validated runtime configuration;
* health and dependency-aware readiness checks;
* resilient MQTT reconnect behavior;
* MQTT username/password authentication and TLS support;
* optional MQTT client certificates for mTLS-capable brokers;
* Prometheus-compatible metrics and a Grafana dashboard;
* Linux cgroup v2 CPU and memory resource awareness;
* container memory usage, limits, headroom, and utilization metrics;
* inference concurrency and model-footprint metrics;
* resource-aware runtime benchmarking;
* throughput, latency, CPU, memory, and inference-efficiency measurements;
* evidence-backed ONNX execution profiles for constrained edge runtimes;
* a live node-local `edgepulse-top` operational TUI;
* rolling CPU and inference-rate trends;
* graceful degraded telemetry handling;
* Docker Compose integration testing across the real HTTP and MQTT paths;
* Helm-based Kubernetes deployment;
* Kubernetes Secret references for MQTT credentials and TLS material;
* local K3s validation with k3d;
* automated tests and coverage;
* dependency and IaC security checks;
* container SBOM generation and vulnerability scanning;
* GHCR image publishing and keyless Cosign signing.

## Current version

Current project and chart version: **`0.9.0`**.

The Helm chart metadata and published runtime image use the same application version:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

## Runtime endpoints

| Endpoint          | Purpose                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- |
| `GET /healthz`    | Liveness: confirms that the process is running.                                                                     |
| `GET /readyz`     | Readiness: confirms that the runtime can serve inference; when MQTT is enabled, MQTT connectivity is also required. |
| `GET /model/info` | Returns model, active artifact, manifest verification, backend, and execution-profile metadata.                     |
| `POST /infer`     | Runs inference for HTTP telemetry.                                                                                  |
| `GET /metrics`    | Exposes Prometheus-compatible application and resource metrics.                                                     |

## Inference backends

| Backend      | Purpose                                                                 |
| ------------ | ----------------------------------------------------------------------- |
| `rule-based` | Lightweight deterministic anomaly scoring for runtime/platform testing. |
| `onnx`       | ONNX Runtime inference using the packaged anomaly-scoring model.        |

Select the backend with:

```bash
MODEL_BACKEND=rule-based
# or
MODEL_BACKEND=onnx
```

When ONNX mode is selected, the runtime loads the configured model during application startup. A model initialization failure makes `/readyz` report not ready.

## ONNX model variants

EdgePulse packages two ONNX artifacts:

| Variant | Artifact                                 |          Size | Purpose                                     |
| ------- | ---------------------------------------- | ------------: | ------------------------------------------- |
| FP32    | `runtime/models/anomaly_score.onnx`      | 135,289 bytes | Reference weight-bearing FP32 model.        |
| INT8    | `runtime/models/anomaly_score_int8.onnx` |  40,175 bytes | Dynamically quantized CPU-oriented variant. |

The INT8 artifact is approximately **70.3% smaller** than the FP32 artifact.

The FP32 model is deterministic and intentionally synthetic. It preserves the original EdgePulse anomaly-score semantics while introducing real weight tensors and matrix operations that make model optimization and quantization experiments meaningful.

The model is not presented as a trained production anomaly detector. Its purpose is to provide a realistic inference artifact for studying deployment, runtime behavior, model packaging, quantization, resource constraints, and operational tooling.

Generate the FP32 artifact with:

```bash
python scripts/create_onnx_model.py
```

Generate the INT8 variant with:

```bash
python scripts/quantize_onnx_model.py
```

Compare their numerical behavior with:

```bash
python scripts/compare_onnx_models.py
```

The validation sweep used 1,501 score points across the range `0.0` to `1.5`.

Observed results:

```text
mean absolute error:       ~0.000117
p95 absolute error:        ~0.000222
maximum absolute error:    ~0.000234
classification mismatches: 0 / 1501
```

These results describe the current deterministic EdgePulse model only.

### Selecting the active artifact

The model and its manifest are selected independently but are expected to match:

```text
MODEL_PATH
MODEL_MANIFEST_PATH
```

FP32:

```bash
MODEL_BACKEND=onnx \
MODEL_PATH=/app/models/anomaly_score.onnx \
MODEL_MANIFEST_PATH=/app/models/model-manifest.json \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build edgepulse-runtime
```

INT8:

```bash
MODEL_BACKEND=onnx \
MODEL_PATH=/app/models/anomaly_score_int8.onnx \
MODEL_MANIFEST_PATH=/app/models/model-manifest-int8.json \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build edgepulse-runtime
```

`GET /model/info` reports both the selected paths and manifest verification state.

Relevant fields include:

```text
model_path
model_manifest_path
artifact_filename
artifact_size_bytes
artifact_sha256
artifact_sha256_verified
active_model_matches_manifest
```

This distinguishes two different checks:

```text
artifact_sha256_verified
    -> the artifact described by the manifest has the expected content

active_model_matches_manifest
    -> the runtime is actually serving the artifact described by that manifest
```

This prevents a valid FP32 manifest from being mistaken for verification of an active INT8 model, or vice versa.

## ONNX execution profiles

ONNX inference can be configured with:

```text
EXECUTION_PROFILE
```

Current profiles:

| Profile    | ONNX strategy                                                                             | Intended use                                     |
| ---------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `eco`      | One intra-op thread, sequential execution, thread spinning disabled.                      | Constrained edge execution and CPU efficiency.   |
| `balanced` | ONNX Runtime automatic intra-op threading, sequential execution, thread spinning enabled. | General-purpose/default ONNX execution baseline. |

The default is:

```text
EXECUTION_PROFILE=balanced
```

Example:

```bash
MODEL_BACKEND=onnx \
EXECUTION_PROFILE=eco \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build --force-recreate edgepulse-runtime
```

The resolved execution profile is exposed through:

```text
GET /model/info
```

Execution profiles apply only to the ONNX backend. When the rule-based backend is selected, the configured profile is reported but marked inactive.

The profiles were selected through benchmark experiments rather than assumed from their names. More aggressive parallel and latency-oriented candidates were tested and rejected because they did not provide useful tradeoffs for the constrained test budget.

Execution-profile tuning and model quantization are separate concerns:

```text
model variant
    -> FP32 or INT8 representation

execution profile
    -> how ONNX Runtime uses available CPU resources
```

The FP32-versus-INT8 comparison uses the same `eco` execution profile so the model representation is the primary changed variable.

## Quick start: secured Docker Compose stack

The Compose environment uses an authenticated TLS-enabled Mosquitto broker. Test PKI material and the local password database are generated into an ephemeral Docker volume; private keys are not committed to the repository.

The runtime is constrained to an edge-oriented local resource budget:

```text
CPU:     0.5 core
Memory:  512 MiB
```

EdgePulse discovers these limits through Linux cgroup v2 rather than through application-specific hard-coded configuration.

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

Application and dependency metrics include:

```text
edgepulse_device_messages_total
edgepulse_inference_requests_total
edgepulse_inference_latency_seconds
edgepulse_inference_errors_total
edgepulse_inference_in_progress

edgepulse_mqtt_connected
edgepulse_mqtt_messages_total
edgepulse_mqtt_errors_total

edgepulse_model_info
edgepulse_model_artifact_size_bytes
```

Resource metrics include:

```text
edgepulse_resource_cgroup_v2_available

edgepulse_resource_memory_current_bytes
edgepulse_resource_memory_peak_bytes
edgepulse_resource_memory_limited
edgepulse_resource_memory_limit_bytes
edgepulse_resource_memory_headroom_bytes
edgepulse_resource_memory_utilization_ratio

edgepulse_resource_cpu_limited
edgepulse_resource_cpu_limit_cores
```

The Prometheus Python client also exposes process metrics including:

```text
process_cpu_seconds_total
process_resident_memory_bytes
```

The distinction is intentional:

```text
process metrics
    -> Python process behavior

cgroup metrics
    -> container resource consumption and budget
```

Inference latency uses explicit sub-millisecond histogram buckets so local and Prometheus-based tooling can estimate useful latency percentiles for the current lightweight ONNX workload.

Example checks:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_connected
curl -s http://localhost:8080/metrics | grep edgepulse_resource
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
curl -s http://localhost:8080/metrics | grep 'model_backend="onnx"'
```

A Grafana dashboard is available at:

```text
dashboards/grafana/edgepulse-overview.json
```

The dashboard includes application traffic, inference behavior, MQTT state, model metadata, and an **Edge Resource Efficiency** section for CPU and memory budget visibility.

See [docs/observability.md](docs/observability.md) for PromQL examples and [docs/servicemonitor.md](docs/servicemonitor.md) for Prometheus Operator integration.

## `edgepulse-top`

EdgePulse includes a live terminal dashboard for immediate node-local operational visibility:

```text
scripts/edgepulse_top.py
```

Install the local tooling dependency:

```bash
pip install -r requirements-tools.txt
```

Run the live dashboard:

```bash
python scripts/edgepulse_top.py
```

The dashboard consumes the runtime's existing HTTP and Prometheus interfaces rather than creating a separate monitoring path.

It displays:

* liveness and readiness;
* MQTT connection state;
* telemetry scrape state;
* model name and version;
* inference backend;
* ONNX execution profile;
* model artifact size;
* CPU usage versus cgroup CPU budget;
* memory usage, limit, utilization, and headroom;
* inference request rate;
* inference concurrency;
* inference error rate;
* MQTT message and error rates;
* histogram-derived inference p50/p95/p99 latency;
* rolling CPU-utilization and inference-rate trends.

Resource pressure is intentionally distinguished from failure.

For example, CPU utilization approaching the configured quota is shown as a warning/busy condition rather than automatically declaring the runtime unhealthy. Memory pressure uses more conservative warning thresholds because exhaustion can result in OOM termination.

Transient telemetry failures also preserve the last successfully collected dashboard:

```text
successful polls
      |
      v
     LIVE

single/transient failures
      |
      v
   DEGRADED
   last-known state retained

repeated failures
      |
      v
  UNREACHABLE
```

Single-snapshot modes are also available:

```bash
python scripts/edgepulse_top.py --once
python scripts/edgepulse_top.py --json
```

The tool intentionally has a different responsibility from Grafana:

```text
edgepulse-top
    -> immediate state of one edge runtime

Grafana
    -> historical and fleet-oriented visibility
```

See [docs/edgepulse-top.md](docs/edgepulse-top.md) for architecture, metrics, rate calculations, histogram percentile behavior, and usage.

## Runtime benchmarking

EdgePulse includes a lightweight benchmark client:

```text
scripts/benchmark_runtime.py
```

Example:

```bash
python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 2 \
  --output /tmp/edgepulse-benchmark.json
```

The benchmark measures:

* throughput;
* client p50/p95/p99 latency;
* inference p50/p95/p99 latency;
* CPU consumption;
* CPU-budget utilization;
* average and maximum observed memory;
* memory budget and headroom;
* inferences per CPU-second;
* the active execution profile;
* active model path and manifest path;
* artifact filename and size;
* artifact SHA-256 and verification state;
* whether the active model matches the selected manifest.

A concurrency sweep can be used to identify where additional parallelism stops producing useful throughput and begins primarily increasing tail latency.

Under the constrained test envelope:

```text
CPU:     0.5 core
Memory:  512 MiB
```

concurrency 2 remains a useful low-latency operating point for the current ONNX workload.

Higher concurrency values are useful as diagnostic stress points. They show where the CPU quota is saturated and requests increasingly wait for CPU rather than producing proportional throughput gains.

### FP32 versus INT8

The final comparison fixed:

```text
backend:            ONNX
execution profile:  eco
CPU:                0.5 core
memory:             512 MiB
warm-up:            2 seconds
duration:           20 seconds
repetitions:        3
concurrency:        1, 2, 4, 8
```

Representative median results:

| Variant |  C | Throughput req/s | Client p95 | Inference p95 | CPU budget | Avg memory | Infer/CPU-s |
| ------- | -: | ---------------: | ---------: | ------------: | ---------: | ---------: | ----------: |
| FP32    |  1 |           463.42 |   2.575 ms |      0.163 ms |      88.7% |   64.2 MiB |     1033.33 |
| FP32    |  2 |           471.48 |   4.422 ms |      0.434 ms |      97.4% |   64.1 MiB |      968.17 |
| FP32    |  4 |           488.95 |  48.472 ms |      0.804 ms |      97.4% |   64.8 MiB |     1004.11 |
| FP32    |  8 |           494.80 |  63.506 ms |      1.198 ms |      97.3% |   65.5 MiB |     1017.27 |
| INT8    |  1 |           458.48 |   3.619 ms |      0.265 ms |      90.6% |   59.5 MiB |     1021.75 |
| INT8    |  2 |           484.89 |   4.199 ms |      0.411 ms |      97.3% |   59.3 MiB |      992.01 |
| INT8    |  4 |           505.94 |  48.792 ms |      0.776 ms |      97.2% |   60.0 MiB |     1041.38 |
| INT8    |  8 |           506.13 |  63.664 ms |      1.159 ms |      97.4% |   60.9 MiB |     1039.63 |

At concurrency 2, INT8 provided approximately:

```text
artifact size:         -70.3%
throughput:             +2.8%
client p95 latency:     -5.0%
inference p95 latency:  -5.3%
average memory:         -7.5%
inferences / CPU-sec:   +2.5%
```

INT8 was not faster at every load level.

At concurrency 1, dynamic quantization overhead outweighed its compute benefits and produced worse latency than FP32.

The measured conclusion is therefore narrower:

> Dynamic INT8 quantization substantially reduces model footprint and modestly improves memory and CPU efficiency under moderate and saturated load, but it is not universally faster than FP32.

### ONNX memory-policy experiment

CPU memory-arena and memory-pattern settings were also tested as possible edge-memory optimizations.

An initial repeated-process experiment appeared to show a large memory saving when allocator features were disabled.

The result did not survive a stricter confirmation experiment that restarted the runtime before every repetition.

Fresh-process medians at concurrency 2 were:

| Policy                       |   Throughput | Client p95 | Avg memory | Max memory |
| ---------------------------- | -----------: | ---------: | ---------: | ---------: |
| Default ONNX memory behavior | 487.66 req/s |   4.488 ms |   59.4 MiB |   72.5 MiB |
| CPU memory arena disabled    | 489.95 req/s |   5.475 ms |   59.2 MiB |   71.8 MiB |

The memory difference was negligible, while p95 latency was worse with the CPU memory arena disabled.

The implementation therefore keeps ONNX Runtime's default memory behavior and does **not** expose a separate memory profile.

This is an intentional negative result: configuration was rejected because its apparent benefit was not repeatable under stricter experimental isolation.

Execution-profile experiments also showed that more ONNX threading is not automatically beneficial in a heavily constrained CPU environment.

These measurements describe the current EdgePulse workload and host environment. They are not intended as general ONNX Runtime performance claims.

See [docs/benchmarking.md](docs/benchmarking.md) for methodology, historical execution-profile experiments, repeatability guidance, and interpretation.

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

Select an ONNX execution profile with:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco
```

Select the INT8 model and matching manifest with:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco \
  --set runtime.env.modelPath=/app/models/anomaly_score_int8.onnx \
  --set runtime.env.modelManifestPath=/app/models/model-manifest-int8.json
```

The chart can deploy the bundled Mosquitto broker and supports secure MQTT configuration through **existing Kubernetes Secrets**. It does not generate production credentials or certificates.

This allows operational ownership to remain clean:

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

* pre-commit hooks;
* Python compilation;
* Ruff lint and formatting;
* pytest runtime tests with coverage;
* Helm lint and template rendering;
* Docker image builds;
* Python dependency audits;
* Checkov Helm/Dockerfile scanning;
* secured Docker Compose E2E validation.

Separate workflows provide:

* SPDX SBOM generation;
* container vulnerability scanning;
* GHCR image publishing;
* keyless Cosign image signing.

See:

* [docs/security.md](docs/security.md)
* [docs/container-security.md](docs/container-security.md)
* [docs/release.md](docs/release.md)
* [docs/image-signing.md](docs/image-signing.md)

## Repository structure

```text
.
├── charts/
│   └── edgepulse-runtime/        # Helm chart and deployment values
├── dashboards/
│   └── grafana/                  # Importable Grafana dashboard
├── deploy/
│   └── docker-compose/           # Secured local integration environment
├── docs/                         # Architecture, operations, benchmarking, security guides
├── runtime/                      # FastAPI runtime, inference backends, execution profiles, tests
├── scripts/                      # Benchmark, edgepulse-top, model, and E2E utilities
└── simulators/                   # Simulated edge-device producers
```

## Documentation map

| Document                                         | Use it for                                                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [Architecture](docs/architecture.md)             | Components, data paths, readiness, security boundaries.                                           |
| [Demo walkthrough](docs/demo-walkthrough.md)     | A concise technical demonstration of the project.                                                 |
| [Local k3d/K3s](docs/k3d-k3s-local.md)           | Kubernetes validation on a workstation.                                                           |
| [Observability](docs/observability.md)           | Application/resource metrics, PromQL, Grafana, MQTT connectivity.                                 |
| [`edgepulse-top`](docs/edgepulse-top.md)         | Live node-local operational TUI, rates, trends, and degraded telemetry behavior.                  |
| [Runtime benchmarking](docs/benchmarking.md)     | Saturation, execution profiles, FP32/INT8 comparison, resource efficiency, and experiment design. |
| [ServiceMonitor](docs/servicemonitor.md)         | Prometheus Operator integration.                                                                  |
| [Security](docs/security.md)                     | Runtime, MQTT, Kubernetes, and CI security posture.                                               |
| [Container security](docs/container-security.md) | SBOM and vulnerability scan workflow.                                                             |
| [Release](docs/release.md)                       | Version-tagged GHCR publication workflow.                                                         |
| [Image signing](docs/image-signing.md)           | Keyless Cosign signing and verification.                                                          |
| [Troubleshooting](docs/troubleshooting.md)       | Runtime, MQTT, TLS, Compose, and Kubernetes diagnostics.                                          |
| [Roadmap](docs/project-roadmap.md)               | Current state and next production-oriented increments.                                            |

## Scope

EdgePulse is deliberately small enough to understand end to end. Its purpose is to demonstrate the operational path of an AI workload—from telemetry ingestion through inference, model packaging and optimization, deployment, observability, resource management, benchmarking, execution tuning, local operations, security, and release—without hiding the core concepts behind a large framework.

It is not intended to be a complete device-management platform, training platform, or production MQTT PKI system.

The packaged ONNX model is an infrastructure workload rather than a claim of production ML quality. A trained domain model can later replace it without redesigning the surrounding runtime, deployment, manifest, quantization, observability, or benchmarking layers.

## License

Apache License 2.0. See [LICENSE](LICENSE).
