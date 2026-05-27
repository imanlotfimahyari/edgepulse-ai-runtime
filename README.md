# EdgePulse AI Runtime

EdgePulse AI Runtime is a lightweight edge-AI runtime for industrial and IoT environments.

It ingests telemetry from simulated edge devices over HTTP or MQTT, runs local anomaly/inference logic, exposes Prometheus-compatible metrics, and can be deployed with Docker Compose. Kubernetes and Helm deployment are planned next.

The project focuses on the platform layer around edge AI:

- telemetry ingestion;
- containerized runtime packaging;
- local inference/anomaly detection;
- HTTP and MQTT ingestion paths;
- health and readiness endpoints;
- Prometheus-compatible metrics;
- repeatable local deployment with Docker Compose.

This is not an ML research project. The goal is to show how edge-AI workloads can be packaged, operated, observed, and deployed in a production-shaped way.

## Current version

`v0.2.0` includes:

- FastAPI runtime;
- HTTP `/infer` endpoint;
- MQTT telemetry consumer;
- Mosquitto broker through Docker Compose;
- rule-based anomaly detector;
- simulated vibration, temperature, power-meter, and camera-like devices;
- Prometheus-compatible metrics;
- ingestion labels for `http` and `mqtt`;
- Docker Compose deployment.

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

## MQTT development note for WSL

When testing MQTT from WSL with Docker Compose, make sure there is no local Mosquitto service already listening on port `1883`.

Check:

```bash
sudo ss -ltnp | grep ':1883' || true
```

If a local Mosquitto service is running, stop it before using the Docker Compose broker:

```bash
sudo systemctl stop mosquitto || true
sudo pkill mosquitto || true
```

The simulators use `127.0.0.1` as the MQTT host to avoid `localhost` ambiguity in WSL/Docker Desktop environments.

## Roadmap

- Add Helm chart for Kubernetes deployment.
- Add K3s/kind deployment documentation.
- Add ONNX Runtime backend.
- Add Grafana dashboard and Prometheus query examples.
- Add GitHub Actions CI.
- Add container scan workflow.
