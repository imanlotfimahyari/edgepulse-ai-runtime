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
```

## Run locally with Docker Compose

Start the runtime:

```bash
docker compose -f deploy/docker-compose/docker-compose.yaml up --build
```

In another terminal, test the runtime:

```bash
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/readyz | jq
curl -s http://localhost:8080/model/info | jq
curl -s http://localhost:8080/metrics | grep edgepulse
```

Run the vibration simulator:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 10 \
  --anomaly-rate 0.30
```

Stop the runtime:

```bash
docker compose -f deploy/docker-compose/docker-compose.yaml down
```

## Runtime endpoints

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Runtime health check |
| `GET /readyz` | Runtime readiness and model backend status |
| `GET /model/info` | Current model metadata |
| `POST /infer` | Telemetry inference/anomaly endpoint |
| `GET /metrics` | Prometheus-compatible metrics |

## Current milestone

The first milestone implements a FastAPI-based edge runtime with rule-based anomaly detection, Prometheus-compatible metrics, Docker Compose packaging, and a simulated vibration sensor that sends telemetry to the inference endpoint.

## Roadmap

- Add temperature, power-meter, and camera-like simulated devices.
- Add MQTT support with Mosquitto.
- Add Helm chart for Kubernetes deployment.
- Add K3s/RKE2 deployment documentation.
- Add ONNX Runtime backend.
- Add Grafana dashboard and GitHub Actions CI.

## Run all simulated edge devices

The project includes multiple simulated edge devices. Each device sends synthetic telemetry to the EdgePulse runtime and receives a normal/anomaly prediction.

Run the vibration sensor:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30

## MQTT development note for WSL

When testing MQTT from WSL with Docker Compose, make sure there is no local Mosquitto service already listening on port `1883`.

Check:

```bash
sudo ss -ltnp | grep ':1883' || true
