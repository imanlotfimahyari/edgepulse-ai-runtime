# EdgePulse AI Runtime

EdgePulse AI Runtime is a lightweight edge-AI runtime for industrial and IoT environments.

It ingests telemetry from simulated edge devices, runs local anomaly/inference logic, exposes Prometheus metrics, and can be deployed with Docker or lightweight Kubernetes.

The project focuses on the platform layer around edge AI:

- telemetry ingestion;
- containerized runtime packaging;
- local inference/anomaly detection;
- health and readiness endpoints;
- Prometheus-compatible metrics;
- repeatable deployment using Docker Compose now, and Kubernetes/Helm later.

This is not an ML research project. The goal is to show how edge-AI workloads can be packaged, operated, observed, and deployed in a production-shaped way.

## Current version

`v0.1.0` includes:

- FastAPI runtime;
- rule-based anomaly detector;
- vibration sensor simulator;
- Docker Compose deployment;
- Prometheus metrics endpoint.

## Architecture

```text
Simulated Vibration Sensor
        |
        | HTTP
        v
EdgePulse AI Runtime
        |
        | /metrics
        v
Prometheus-compatible metrics
