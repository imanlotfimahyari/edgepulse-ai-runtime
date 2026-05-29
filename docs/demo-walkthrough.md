# EdgePulse Demo Script

This document provides a short demo flow for presenting EdgePulse AI Runtime.

## Demo goal

Show that EdgePulse is not only an inference API. It is a production-shaped edge-AI runtime with:

- simulated edge devices;
- HTTP and MQTT ingestion;
- local inference;
- Prometheus metrics;
- Docker Compose deployment;
- Helm/Kubernetes deployment;
- CI, security scanning, SBOM generation, image signing, and model artifact versioning.

## 5-minute demo

### 1. Explain the problem

Industrial and IoT environments often need local inference close to edge devices.

Sending every telemetry event to a central cloud system can be expensive, slow, or unreliable when connectivity is limited.

EdgePulse demonstrates how an edge runtime can receive device telemetry, run local anomaly detection, expose metrics, and be packaged for container/Kubernetes environments.

### 2. Start the local stack

```bash
docker compose -f deploy/docker-compose/docker-compose.yaml up --build
```

This starts:

- EdgePulse Runtime;
- Mosquitto MQTT broker.

### 3. Check runtime health

```bash
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/readyz | jq
curl -s http://localhost:8080/model/info | jq
```

Important things to show:

- runtime is healthy;
- MQTT is enabled;
- model metadata is exposed;
- model manifest is available;
- model checksum verification succeeds.

### 4. Run simulated devices over HTTP

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Explain that this simulates a device calling the runtime directly through HTTP.

### 5. Run simulated devices over MQTT

```bash
python3 -m simulators.temperature_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Explain that MQTT is closer to many edge/IoT deployments where devices publish telemetry to topics.

### 6. Check metrics

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_device_messages_total
curl -s http://localhost:8080/metrics | grep edgepulse_inference_requests_total
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
```

Important things to show:

- messages are counted by device type;
- inference requests are counted by ingestion type;
- MQTT messages are visible separately;
- metrics are Prometheus-compatible.

### 7. Explain Kubernetes path

Show the Helm chart:

```bash
tree charts/edgepulse-runtime
```

Then explain that the same runtime can be deployed with Helm to K3s/k3d or a real Kubernetes cluster.

### 8. Explain release/security path

Show the workflows:

```bash
ls .github/workflows
```

Mention:

- CI validation;
- dependency audit;
- Checkov IaC checks;
- container SBOM and vulnerability scan;
- GHCR image publishing;
- Cosign image signing.

## 10-minute demo extension

If there is more time, also show:

```bash
helm lint charts/edgepulse-runtime
helm template edgepulse-runtime charts/edgepulse-runtime > /tmp/edgepulse-rendered.yaml
```

Then show:

```bash
grep -n "kind: NetworkPolicy\|readinessProbe\|livenessProbe\|ServiceMonitor" /tmp/edgepulse-rendered.yaml
```

This demonstrates Kubernetes operational maturity:

- health checks;
- network policy;
- service monitor support;
- resource requests and limits;
- non-root runtime settings.

## Closing statement

EdgePulse is a small project, but it demonstrates the full lifecycle of an edge-AI workload:

```text
device telemetry
-> HTTP/MQTT ingestion
-> local inference
-> metrics
-> container packaging
-> Kubernetes deployment
-> CI/security validation
-> signed release image
-> versioned model artifact
```
