# Project Roadmap

This document describes possible next steps for EdgePulse AI Runtime.

## Current state

EdgePulse currently includes:

- simulated edge devices;
- HTTP telemetry ingestion;
- MQTT telemetry ingestion;
- local anomaly scoring;
- ONNX model artifact support;
- model manifest and checksum verification;
- Prometheus-compatible metrics;
- Grafana dashboard;
- Docker Compose deployment;
- Helm chart for Kubernetes;
- local K3s/k3d validation;
- ServiceMonitor support;
- CI checks;
- dependency audit;
- Checkov IaC scanning;
- container SBOM generation;
- vulnerability scan artifact;
- GHCR image publishing;
- Cosign image signing.

## Near-term improvements

### 1. MQTT authentication and TLS

Current MQTT setup is intentionally simple for local development.

Production improvement:

- enable username/password authentication;
- support TLS listener;
- mount broker credentials from Kubernetes Secret;
- document local and Kubernetes secure MQTT setup.

### 2. Device identity

Current simulators send a `device_id` and `device_type`, but there is no device registry.

Production improvement:

- define device identity model;
- validate known devices;
- reject unknown device IDs;
- add per-device metadata;
- track device source and tenant/location labels.

### 3. Realistic model lifecycle

Current ONNX model is a demo artifact.

Production improvement:

- add training pipeline;
- generate model from sample dataset;
- store training metadata;
- track model input schema;
- sign model artifacts;
- support model registry integration.

### 4. Runtime backend selection

Current runtime can expose model metadata and has ONNX artifact support.

Production improvement:

- make backend selection clearer;
- support rule-based and ONNX backends as explicit runtime modes;
- validate model availability on startup when ONNX mode is selected;
- fail readiness if configured model backend cannot load.

### 5. End-to-end tests

Production improvement:

- start Docker Compose in CI;
- run HTTP simulator;
- run MQTT simulator;
- assert metrics are produced;
- assert `/model/info` verifies model checksum.

### 6. GitOps deployment example

Production improvement:

- add Argo CD Application example;
- document Helm values for Kubernetes deployment;
- document image tag promotion flow.

### 7. Observability improvements

Production improvement:

- add alert examples;
- add PrometheusRule template;
- add Grafana panels for latency percentiles;
- add MQTT-specific dashboard panels;
- add OpenTelemetry tracing.

### 8. Scaling and reliability

Production improvement:

- define MQTT consumer scaling model;
- avoid duplicate consumption when replicas increase;
- add durable queue or shared subscription design;
- add retry/dead-letter behavior for malformed telemetry.

## Longer-term production direction

A production-grade version of this project would include:

- secure MQTT ingestion;
- device registry;
- model registry;
- signed model artifacts;
- policy-controlled Kubernetes deployment;
- GitOps promotion;
- telemetry storage;
- edge-to-cloud synchronization;
- offline operation mode;
- fleet-level observability.

## What should not be overbuilt yet

Avoid overbuilding these too early:

- complex ML training pipeline;
- large frontend UI;
- multi-cloud abstractions;
- heavy service mesh integration;
- distributed database;
- custom Kubernetes operator.

The current value of the project is that it stays compact while still showing production-oriented platform thinking.
