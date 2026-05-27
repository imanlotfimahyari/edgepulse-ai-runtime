# Local K3s Deployment with k3d

This guide runs EdgePulse AI Runtime on a local K3s cluster using k3d.

k3d runs real K3s inside Docker containers, which makes it convenient for laptop-based Kubernetes testing.

## Prerequisites

Required tools:

- Docker Desktop with WSL integration enabled
- k3d
- kubectl
- Helm

Check:

```bash
docker version
k3d version
kubectl version --client
helm version
```

## Create the local K3s cluster

```bash
k3d cluster create edgepulse \
  --servers 1 \
  --agents 1
```

Check the nodes:

```bash
kubectl get nodes -o wide
```

Expected result:

```text
k3d-edgepulse-server-0   Ready
k3d-edgepulse-agent-0    Ready
```

## Build and import the runtime image

Build the runtime image:

```bash
docker build -t edgepulse-runtime:0.2.0 ./runtime
```

Import it into the k3d cluster:

```bash
k3d image import edgepulse-runtime:0.2.0 -c edgepulse
```

This is required because the K3s cluster runs inside Docker and does not automatically see every local Docker image.

## Install the Helm chart

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.image.repository=edgepulse-runtime \
  --set runtime.image.tag=0.2.0 \
  --set runtime.image.pullPolicy=IfNotPresent
```

## Check Kubernetes resources

```bash
kubectl -n edgepulse get all
kubectl -n edgepulse get pods -o wide
```

Expected pods:

```text
edgepulse-runtime-...        1/1 Running
edgepulse-runtime-mqtt-...   1/1 Running
```

## Check logs

```bash
kubectl -n edgepulse logs deploy/edgepulse-runtime
kubectl -n edgepulse logs deploy/edgepulse-runtime-mqtt
```

The runtime logs should show that the MQTT consumer started and connected successfully.

Expected runtime log pattern:

```text
Starting MQTT consumer host=edgepulse-runtime-mqtt port=1883 topic=edge/devices/+/telemetry
MQTT connected reason_code=Success
```

## Port-forward the runtime service

Open a terminal and keep this command running:

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime 8080:8080
```

In another terminal, test the runtime:

```bash
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/readyz | jq
curl -s http://localhost:8080/model/info | jq
```

Expected readiness response:

```json
{
  "status": "ready",
  "model_name": "edgepulse-anomaly-detector",
  "model_version": "0.2.0",
  "model_backend": "rule-based",
  "mqtt_enabled": true
}
```

## Test HTTP ingestion

With the runtime port-forward still running:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Check HTTP metrics:

```bash
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
```

Expected result: metrics should include `ingestion="http"`.

## Port-forward the MQTT broker

Open another terminal and keep this command running:

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime-mqtt 1883:1883
```

If WSL has a local Mosquitto service already using port `1883`, stop it first:

```bash
sudo systemctl stop mosquitto || true
sudo pkill mosquitto || true
```

Check port usage:

```bash
sudo ss -ltnp | grep ':1883' || true
```

Expected result while port-forward is active:

```text
kubectl ... 127.0.0.1:1883
```

## Test MQTT ingestion

With both port-forwards running, publish telemetry from all simulated devices:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30

python3 -m simulators.temperature_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30

python3 -m simulators.power_meter.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30

python3 -m simulators.camera_device.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Check MQTT metrics:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
curl -s http://localhost:8080/metrics | grep edgepulse_device_messages_total
```

Expected result: metrics should include all four device types:

```text
device_type="vibration_sensor"
device_type="temperature_sensor"
device_type="power_meter"
device_type="camera_device"
```

## Uninstall the Helm release

```bash
helm uninstall edgepulse-runtime -n edgepulse
kubectl delete namespace edgepulse
```

## Delete the k3d cluster

```bash
k3d cluster delete edgepulse
```
