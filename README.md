# EdgePulse AI Runtime

EdgePulse AI Runtime is a lightweight edge-AI runtime for industrial and IoT environments.

It ingests telemetry from simulated edge devices over HTTP or MQTT, runs local anomaly/inference logic, exposes Prometheus-compatible metrics, and can be deployed locally with Docker Compose or on Kubernetes with Helm.

The project focuses on the platform layer around edge AI:

- telemetry ingestion;
- containerized runtime packaging;
- local inference/anomaly detection;
- HTTP and MQTT ingestion paths;
- health and readiness endpoints;
- Prometheus-compatible metrics;
- Docker Compose deployment;
- Helm-based Kubernetes deployment;
- local K3s validation with k3d;
- CI validation with GitHub Actions.

This is not an ML research project. The goal is to show how edge-AI workloads can be packaged, operated, observed, and deployed in a production-shaped way.

## Current version

`v0.4.0` includes:

- FastAPI runtime;
- HTTP `/infer` endpoint;
- MQTT telemetry consumer;
- Mosquitto broker through Docker Compose and Helm;
- rule-based anomaly detector;
- simulated vibration, temperature, power-meter, and camera-like devices;
- Prometheus-compatible metrics;
- ingestion labels for `http` and `mqtt`;
- Docker Compose deployment;
- Helm chart for Kubernetes deployment;
- local K3s/k3d deployment documentation;
- GitHub Actions CI for pre-commit, Python checks, Helm rendering, and Docker image build.

## Architecture

```text
                 +-----------------------------+
                 | Simulated Edge Devices      |
                 |-----------------------------|
                 | vibration_sensor            |
                 | temperature_sensor          |
                 | power_meter                 |
                 | camera_device               |
                 +--------------+--------------+
                                |
                    HTTP / MQTT |
                                v
+-------------------+      +-----------------------------+
| Mosquitto MQTT    | ---> | EdgePulse AI Runtime        |
| Broker            |      |-----------------------------|
| edge/devices/...  |      | FastAPI                     |
+-------------------+      | MQTT consumer               |
                           | rule-based inference        |
                           | Prometheus metrics          |
                           +--------------+--------------+
                                          |
                                          v
                           GET /metrics for observability
```

## Repository structure

```text
.
├── charts/
│   └── edgepulse-runtime/        # Helm chart
├── deploy/
│   └── docker-compose/           # Local Docker Compose stack
├── docs/
│   ├── architecture.md           # Runtime architecture notes
│   ├── k3d-k3s-local.md          # Local K3s deployment guide
│   └── troubleshooting.md        # Local troubleshooting notes
├── runtime/                      # FastAPI runtime
└── simulators/                   # HTTP/MQTT simulated edge devices
```

## Run locally with Docker Compose

Start the runtime and MQTT broker:

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

Stop the stack:

```bash
docker compose -f deploy/docker-compose/docker-compose.yaml down
```

## Runtime endpoints

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Runtime health check |
| `GET /readyz` | Runtime readiness and MQTT status |
| `GET /model/info` | Current model metadata |
| `POST /infer` | HTTP telemetry inference/anomaly endpoint |
| `GET /metrics` | Prometheus-compatible metrics |

## Run simulated devices over HTTP

Run the vibration sensor:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the temperature sensor:

```bash
python3 -m simulators.temperature_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the power meter:

```bash
python3 -m simulators.power_meter.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the camera-like device:

```bash
python3 -m simulators.camera_device.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

## Run simulated devices over MQTT

Make sure Docker Compose is running first.

Run the vibration sensor:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the temperature sensor:

```bash
python3 -m simulators.temperature_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the power meter:

```bash
python3 -m simulators.power_meter.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

Run the camera-like device:

```bash
python3 -m simulators.camera_device.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --interval-seconds 1 \
  --count 5 \
  --anomaly-rate 0.30
```

## Check metrics

Check MQTT messages:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
```

Check ingestion-specific inference metrics:

```bash
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
```

Check device messages:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_device_messages_total
```

## Run on local K3s with k3d

See:

```text
docs/k3d-k3s-local.md
```

Short version:

```bash
k3d cluster create edgepulse \
  --servers 1 \
  --agents 1

docker build -t edgepulse-runtime:0.2.0 ./runtime
k3d image import edgepulse-runtime:0.2.0 -c edgepulse

helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.image.repository=edgepulse-runtime \
  --set runtime.image.tag=0.2.0 \
  --set runtime.image.pullPolicy=IfNotPresent
```

Check:

```bash
kubectl -n edgepulse get pods -o wide
```

Expected:

```text
edgepulse-runtime-...        1/1 Running
edgepulse-runtime-mqtt-...   1/1 Running
```

## CI

GitHub Actions validates:

- pre-commit checks;
- Python syntax/import checks;
- Ruff lint;
- Ruff format check;
- Helm lint;
- Helm template rendering;
- Docker image build.

## MQTT development note for WSL

When testing MQTT from WSL with Docker Compose or port-forwarding, make sure there is no local Mosquitto service already listening on port `1883`.

Check:

```bash
sudo ss -ltnp | grep ':1883' || true
```

If a local Mosquitto service is running, stop it before using the Docker Compose broker or Kubernetes port-forward:

```bash
sudo systemctl stop mosquitto || true
sudo pkill mosquitto || true
```

The simulators use `127.0.0.1` as the MQTT host to avoid `localhost` ambiguity in WSL/Docker Desktop environments.

## Roadmap

- Add ONNX Runtime backend.
- Add model artifact loading and backend selection.
- Add Grafana dashboard and Prometheus query examples.
- Add container scan workflow.
- Add optional Kubernetes ServiceMonitor support.
- Add release versioning and image publishing workflow.
