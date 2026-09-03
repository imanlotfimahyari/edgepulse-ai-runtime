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
connectivity-aware edge behavior
       |
offline autonomy
       |
model lifecycle
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

### Resource-aware ONNX execution

EdgePulse now supports two benchmark-informed execution profiles:

```text
eco
balanced
```

`eco` uses:

* one ONNX intra-op thread;
* sequential graph execution;
* disabled thread spinning.

`balanced` uses:

* ONNX Runtime automatic intra-op threading;
* sequential graph execution;
* enabled thread spinning.

The selected profile is configurable through `EXECUTION_PROFILE`, exposed through `/model/info`, available through Docker Compose and Helm, and recorded in benchmark JSON output.

Profile design was driven by measurements rather than names.

Parallel graph execution was tested as a performance-oriented candidate and rejected because it performed very poorly for the current tiny ONNX graph under the 0.5-core resource limit.

A separate single-threaded spinning candidate was tested for latency-oriented behavior and removed because it did not provide a repeatable latency advantage.

This leaves two simple and evidence-backed policies rather than several arbitrary presets.

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

### 1. Local edge operational TUI

Add a lightweight terminal interface:

```text
edgepulse-top
```

The TUI should consume the same telemetry already exposed through Prometheus rather than introducing a second monitoring model.

Useful local views include:

* readiness;
* model/backend;
* execution profile;
* MQTT connectivity;
* CPU usage versus budget;
* memory usage versus budget;
* memory headroom;
* inference rate;
* p50/p95 latency;
* inference concurrency;
* errors;
* future edge/cloud connectivity state.

The roles should remain distinct:

```text
edgepulse-top
    -> immediate local edge-node state

Grafana
    -> historical and fleet-oriented observability
```

### 2. ONNX optimization, memory policy, and quantization

Use the benchmark framework to compare model execution variants.

Useful experiments include:

* ONNX Runtime graph optimization;
* CPU memory-arena behavior;
* memory-pattern optimization;
* constrained-memory execution;
* FP32 versus quantized models;
* INT8 inference;
* model-size reduction;
* latency and throughput changes;
* memory changes;
* accuracy delta where applicable.

A future memory-oriented policy should be introduced only if measurements demonstrate a useful tradeoff.

### 3. Efficiency dashboard

Extend the Grafana resource-efficiency view with:

* throughput versus CPU budget;
* inferences per CPU-second;
* backend comparison;
* execution-profile comparison;
* saturation indicators;
* benchmark-informed capacity context.

Grafana remains the historical/fleet view; `edgepulse-top` remains the immediate node-local view.

### 4. Connectivity-aware edge operation

Introduce connectivity policies as a separate concern from inference execution.

Potential policies:

```text
realtime
bandwidth-saver
```

`realtime`:

* forward normal telemetry promptly;
* forward anomalies promptly;
* optimize for cloud freshness.

`bandwidth-saver`:

* continue local inference;
* immediately forward important anomalies;
* aggregate or batch normal telemetry;
* reduce uplink bytes and cloud ingestion volume.

Measure:

* bytes transmitted;
* messages transmitted;
* anomaly-delivery latency;
* aggregation ratio;
* local CPU overhead;
* cloud synchronization lag.

Execution profiles and connectivity policies must remain orthogonal:

```text
execution_profile
    -> how local inference consumes compute

connectivity_profile
    -> how edge results use the network
```

### 5. Offline-first operation

After connectivity-aware forwarding exists, add store-and-forward behavior for intermittent WAN connectivity.

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

Useful capabilities include:

* bounded durable buffering;
* reconnect and exponential backoff;
* replay after reconnection;
* duplicate-handling/idempotency strategy;
* priority handling for anomaly events;
* buffer-depth metrics;
* synchronization-lag metrics;
* explicit overflow behavior.

This phase demonstrates distributed-systems concerns such as partial failure, eventual consistency, backpressure, retries, and local autonomy.

### 6. Power-aware experimentation

CPU utilization is not equivalent to electrical power consumption.

Do not introduce a `power-saver` claim until suitable telemetry is available.

Possible future sources include:

* Intel RAPL;
* host hardware energy counters;
* Kepler or equivalent power telemetry where appropriate.

Then EdgePulse could measure:

```text
average watts
joules per inference
inferences per joule
```

This would allow power-aware execution policies to be justified by measured energy consumption rather than CPU proxies.

### 7. Device identity and authorization

Today, `device_id` and `device_type` are payload fields rather than managed identities.

A useful incremental implementation would:

* define a minimal device registry;
* distinguish registered from unknown devices;
* associate identity with site/location metadata;
* add authorization policy for publish topics;
* demonstrate per-device or per-group MQTT ACLs.

### 8. Model lifecycle and artifact delivery

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

### 9. MQTT consumer scaling semantics

Explore:

* shared subscriptions or consumer-group behavior;
* duplicate-processing risks;
* idempotency;
* malformed-message retry/dead-letter behavior;
* reconnect behavior under multiple replicas.

### 10. GitOps deployment

Add Argo CD when repeated declarative promotion becomes useful:

* `Application` or ApplicationSet example;
* environment-specific values;
* immutable image-tag promotion;
* profile/configuration promotion;
* drift and reconciliation demonstration.

### 11. SLO-oriented observability

Extend the current telemetry with:

* PrometheusRule examples;
* MQTT disconnection alerts;
* inference availability targets;
* latency SLOs;
* error-budget panels;
* benchmark-informed capacity thresholds;
* OpenTelemetry tracing.

### 12. Fleet and model control plane

A mature later-stage demonstration could expose:

* fleet runtime health;
* desired model version;
* execution and connectivity policy;
* configuration promotion;
* model delivery;
* rollout health;
* rollback;
* edge-node resource/capacity information.

## Longer-term direction

```text
device identity
      |
secure telemetry
      |
edge inference runtime
      |
compute-aware execution
      |
local observability + benchmarking
      |
connectivity-aware forwarding
      |
offline buffering/replay
      |
edge/cloud synchronization
      |
Kubernetes / fleet operations
      |
model + configuration promotion
```

## What not to overbuild

Avoid adding complexity unless it demonstrates a specific infrastructure concept:

* large frontend UI;
* full ML training platform;
* distributed database without a concrete requirement;
* multi-cloud abstraction layer;
* service mesh by default;
* custom Kubernetes operator before reconciliation logic is genuinely needed;
* bespoke PKI when cert-manager or external PKI already models the lifecycle well;
* custom monitoring stack separate from Prometheus;
* arbitrary execution profiles without benchmark evidence;
* power-saving claims without actual energy measurements.
