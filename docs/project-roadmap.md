# Project Roadmap

EdgePulse is intentionally developed in small, production-oriented increments.

The goal is not to build every edge/ML subsystem. The goal is to make the operational path around AI inference increasingly realistic while keeping the complete system understandable by one engineer.

The broader direction is:

```text
secure edge runtime
       |
resource observability
       |
performance measurement
       |
resource-aware execution
       |
local operational tooling
       |
model optimization
       |
edge-to-cloud behavior
```

## Current state

Implemented today:

### Runtime and inference

* FastAPI inference runtime;
* HTTP telemetry ingestion;
* MQTT telemetry ingestion;
* rule-based inference backend;
* ONNX Runtime backend;
* backend selection through configuration;
* model artifact and metadata exposure;
* model manifest and artifact checksum verification;
* startup validation for the configured backend;
* liveness and dependency-aware readiness;
* inference concurrency instrumentation.

### MQTT reliability and security

* asynchronous MQTT connection and retry behavior;
* connection-state tracking;
* MQTT connectivity metric;
* readiness failure when MQTT is required but disconnected;
* username/password authentication support;
* TLS CA verification;
* optional client certificate/key support;
* secured Docker Compose broker/E2E environment;
* Helm references to existing credential and TLS Secrets.

### Platform

* Docker Compose deployment;
* constrained local runtime resource budget;
* end-to-end Compose validation for HTTP + MQTT;
* Helm chart;
* local k3d/K3s validation;
* NetworkPolicy support;
* optional ServiceMonitor.

### Observability and resource awareness

* Prometheus application metrics;
* Prometheus process metrics;
* Linux cgroup v2 detection;
* cgroup current and peak memory measurements;
* finite memory-limit detection;
* memory headroom and utilization;
* finite CPU-quota detection;
* CPU quota expressed as cores;
* model artifact-size metric;
* inference-in-progress metric;
* Grafana runtime dashboard;
* Grafana Edge Resource Efficiency panels.

The runtime discovers the CPU and memory budget assigned by its execution environment instead of relying on EdgePulse-specific hard-coded resource values.

### Benchmarking and efficiency

* lightweight Python runtime benchmark client;
* warm-up support;
* configurable duration and concurrency;
* client p50/p95/p99 latency measurement;
* runtime inference p50/p95/p99 latency measurement;
* throughput measurement;
* CPU consumption measurement;
* CPU-budget utilization;
* benchmark-specific average memory;
* benchmark-specific maximum observed memory;
* cgroup memory-budget reporting;
* inferences-per-CPU-second efficiency measurement;
* machine-readable JSON results;
* repeated concurrency-sweep validation;
* rule-based versus ONNX comparison under identical resource limits.

Initial experiments demonstrate that the current constrained runtime reaches CPU saturation before memory saturation and that increasing concurrency beyond the useful operating region can substantially increase tail latency for little additional throughput.

### Quality and supply chain

* pytest runtime suite with coverage;
* Ruff lint/format validation;
* pre-commit controls;
* dependency audit;
* Checkov IaC checks;
* container SBOM generation;
* vulnerability scan artifact;
* GHCR image release workflow;
* keyless Cosign signing.

## Recommended next increments

### 1. Resource-aware execution profiles

Resource observability and benchmarking now provide enough information to define runtime profiles based on measured behavior rather than arbitrary configuration.

Introduce profiles such as:

```text
eco
balanced
performance
```

Potential profile controls include:

* ONNX Runtime intra-op thread count;
* ONNX Runtime inter-op thread count;
* execution mode;
* request concurrency;
* application worker configuration.

The objective is to demonstrate deliberate trade-offs between:

```text
throughput
latency
CPU consumption
memory consumption
```

Profiles should remain explicit and understandable rather than becoming a complex adaptive scheduler.

### 2. Local edge operational TUI

Add a lightweight terminal interface such as:

```text
edgepulse-top
```

The TUI should consume the same telemetry already exposed through Prometheus rather than introducing a second monitoring system.

Useful local views include:

* readiness;
* model/backend;
* MQTT connectivity;
* CPU usage versus budget;
* memory usage versus budget;
* memory headroom;
* inference rate;
* p50/p95 latency;
* inference concurrency;
* errors;
* future edge/cloud connectivity state.

The role of the TUI should differ from Grafana:

```text
edgepulse-top
    -> immediate local edge-node state

Grafana
    -> historical and fleet-oriented observability
```

### 3. ONNX optimization and quantization

Use the benchmark framework to compare model execution variants.

Useful experiments include:

* ONNX Runtime session configuration;
* CPU thread tuning;
* graph optimization levels;
* FP32 versus quantized models;
* INT8 inference;
* model-size reduction;
* latency and throughput changes;
* memory changes;
* accuracy delta where applicable.

The benchmark framework should provide the evidence for deciding whether an optimization is useful.

### 4. Device identity and authorization

Today, `device_id` and `device_type` are payload fields rather than managed identities.

A useful incremental implementation would:

* define a minimal device registry;
* distinguish registered from unknown devices;
* associate identity with site/location metadata;
* add authorization policy for publish topics;
* demonstrate per-device or per-group MQTT ACLs.

Avoid building a large device-management product. The objective is to demonstrate identity enforcement around the runtime.

### 5. Model lifecycle and artifact delivery

The runtime already exposes model metadata and verifies the packaged artifact checksum.

A later lifecycle increment can add:

```text
cloud/model source
       |
       v
manifest
       |
       v
download
       |
       v
checksum / signature verification
       |
       v
candidate load
       |
       v
health validation
       |
       +---- success ---> activation
       |
       +---- failure ---> rollback
```

Useful capabilities include:

* model version promotion;
* signed model artifacts;
* input/output schema metadata;
* candidate activation;
* rollback;
* optional lightweight registry integration.

The focus should remain inference infrastructure rather than training.

### 6. MQTT consumer scaling semantics

A single consumer is straightforward; horizontal scaling introduces distributed-systems concerns.

Explore:

* shared subscriptions or consumer-group behavior;
* duplicate-processing risks;
* idempotency strategy;
* malformed-message retry/dead-letter behavior;
* reconnect behavior under multiple replicas.

### 7. GitOps deployment

Add a small Argo CD example when repeated Kubernetes promotion becomes useful:

* Argo CD `Application` or ApplicationSet example;
* environment-specific values;
* immutable image-tag promotion;
* configuration/model-profile promotion;
* drift and reconciliation demonstration.

Do not add GitOps only for a UI. It should demonstrate declarative promotion and reconciliation.

### 8. SLO-oriented observability

Extend the existing metrics and dashboard with:

* PrometheusRule examples;
* MQTT disconnection alerts;
* inference availability targets;
* inference latency SLOs;
* error-budget-oriented panels;
* benchmark-informed capacity thresholds;
* OpenTelemetry tracing for HTTP/MQTT-to-inference paths.

### 9. Edge-to-cloud event synchronization

A later phase should introduce behavior that is specific to disconnected or bandwidth-constrained edge environments.

Useful capabilities include:

* selective forwarding;
* local aggregation of normal telemetry;
* immediate forwarding of anomalies;
* cloud synchronization state;
* synchronization lag metrics.

### 10. Offline buffering and replay

After basic edge/cloud synchronization exists, demonstrate operation during uplink failure:

```text
devices
   |
   v
EdgePulse
   |
   +--> local inference continues
   |
   +--> durable local buffer
              |
         uplink unavailable
              |
         reconnect
              |
              v
            replay
```

This should include:

* bounded local buffering;
* retry/backoff;
* duplicate-handling strategy;
* replay ordering where required;
* buffer-depth metrics;
* synchronization-lag metrics.

### 11. Fleet and model control plane

A mature later-stage demonstration could expose:

* fleet runtime health;
* desired model version;
* configuration/profile promotion;
* model delivery;
* rollout health;
* rollback;
* edge-node resource/capacity information.

This should remain lightweight and should not become a general-purpose device-management product.

## Longer-term direction

A mature EdgePulse demonstration could eventually cover:

```text
device identity
      |
secure telemetry
      |
edge inference runtime
      |
resource-aware execution
      |
local observability + benchmarking
      |
offline buffering
      |
edge/cloud synchronization
      |
Kubernetes / fleet operations
      |
model + configuration promotion
```
