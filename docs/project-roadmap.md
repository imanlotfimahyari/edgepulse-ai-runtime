# Project Roadmap

EdgePulse is intentionally developed in small, production-oriented increments. The goal is not to build every edge/ML subsystem, but to make the operational path around AI inference increasingly realistic.

## Current state

Implemented today:

### Runtime and inference

- FastAPI inference runtime;
- HTTP telemetry ingestion;
- MQTT telemetry ingestion;
- rule-based inference backend;
- ONNX Runtime backend;
- backend selection through configuration;
- model artifact and metadata exposure;
- startup validation for the configured backend;
- liveness and dependency-aware readiness.

### MQTT reliability and security

- asynchronous MQTT connection and retry behavior;
- connection-state tracking;
- MQTT connectivity metric;
- readiness failure when MQTT is required but disconnected;
- username/password authentication support;
- TLS CA verification;
- optional client certificate/key support;
- secured Docker Compose broker/E2E environment;
- Helm references to existing credential and TLS Secrets.

### Platform and observability

- Docker Compose deployment;
- end-to-end Compose validation for HTTP + MQTT;
- Helm chart;
- local k3d/K3s validation;
- NetworkPolicy support;
- optional ServiceMonitor;
- Prometheus metrics;
- Grafana dashboard.

### Quality and supply chain

- pytest runtime suite with coverage;
- Ruff lint/format validation;
- pre-commit controls;
- dependency audit;
- Checkov IaC checks;
- container SBOM generation;
- vulnerability scan artifact;
- GHCR image release workflow;
- keyless Cosign signing.

## Recommended next increments

### 1. Device identity and authorization

Today, `device_id` and `device_type` are payload fields rather than managed identities.

Next useful step:

- define a minimal device registry;
- distinguish registered vs unknown devices;
- associate identity with tenant/site/location metadata;
- add authorization policy for publish topics;
- demonstrate per-device or per-group MQTT ACLs.

Avoid building a large device-management product; the goal is to demonstrate identity enforcement around the runtime.

### 2. Model lifecycle and artifact integrity

The ONNX model is currently a compact demo artifact.

Next useful step:

- formalize model manifest/schema metadata;
- verify model checksum on startup;
- track model input/output schema;
- sign model artifacts;
- demonstrate promotion between model versions;
- optionally integrate a lightweight model registry.

The focus should remain inference infrastructure rather than a full training platform.

### 3. MQTT consumer scaling semantics

A single consumer is straightforward; horizontal scaling introduces message-delivery semantics.

Explore:

- shared subscriptions or consumer-group behavior;
- duplicate-processing risks;
- idempotency strategy;
- malformed-message retry/dead-letter behavior;
- broker reconnect behavior under multiple replicas.

This would add meaningful distributed-systems depth to the project.

### 4. GitOps deployment

Add a small Argo CD example when repeated Kubernetes promotion becomes useful:

- Argo CD `Application` or ApplicationSet example;
- environment-specific values;
- immutable image-tag promotion;
- drift/reconciliation demonstration.

Do not add GitOps only for a UI; add it to demonstrate declarative promotion and reconciliation.

### 5. Observability and SLOs

Extend the current metrics with:

- PrometheusRule examples;
- MQTT disconnection alerts;
- inference availability/latency SLO examples;
- error-budget-oriented dashboard panels;
- OpenTelemetry tracing for HTTP/MQTT to inference.

### 6. Edge-to-cloud behavior

A later phase could demonstrate real edge concerns:

- intermittent uplink;
- local buffering;
- store-and-forward synchronization;
- cloud control-plane/model update flow;
- fleet-level runtime health.

This is more valuable than prematurely adding multi-cloud abstractions.

## Longer-term direction

A mature demonstration could eventually cover:

```text
device identity
      |
secure telemetry
      |
edge inference runtime
      |
local observability + buffering
      |
Kubernetes / fleet operations
      |
model + configuration promotion
      |
edge-to-cloud synchronization
```

## What not to overbuild

Avoid adding complexity unless it demonstrates a specific infrastructure concept:

- large frontend UI;
- full ML training platform;
- distributed database without a concrete requirement;
- multi-cloud abstraction layer;
- service mesh by default;
- custom Kubernetes operator before reconciliation logic is genuinely needed;
- bespoke PKI when cert-manager/external PKI already models the lifecycle well.

The strongest characteristic of EdgePulse is that one engineer can still understand the entire system while it demonstrates realistic platform concerns.
