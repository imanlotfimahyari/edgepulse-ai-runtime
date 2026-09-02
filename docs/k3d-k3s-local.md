# Local K3s Deployment with k3d

This guide runs EdgePulse AI Runtime on a local K3s cluster using k3d.

k3d runs K3s nodes inside Docker containers, which makes it useful for validating the Helm chart and Kubernetes behavior from a workstation.

## Prerequisites

Required:

- Docker Desktop with WSL integration when using Windows/WSL;
- k3d;
- kubectl;
- Helm.

Check:

```bash
docker version
k3d version
kubectl version --client
helm version
```

## Create the cluster

```bash
k3d cluster create edgepulse \
  --servers 1 \
  --agents 1
```

Verify:

```bash
kubectl get nodes -o wide
```

Expected nodes include:

```text
k3d-edgepulse-server-0   Ready
k3d-edgepulse-agent-0    Ready
```

## Option A: use the published image

The chart defaults to:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

If the image is accessible from the cluster, install directly:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace
```

## Option B: test a local image

Build:

```bash
docker build -t edgepulse-runtime:0.9.0 ./runtime
```

Import into k3d:

```bash
k3d image import edgepulse-runtime:0.9.0 -c edgepulse
```

Install using the imported image:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.image.repository=edgepulse-runtime \
  --set runtime.image.tag=0.9.0 \
  --set runtime.image.pullPolicy=IfNotPresent
```

## Check resources

```bash
kubectl -n edgepulse get pods -o wide
kubectl -n edgepulse get svc
kubectl -n edgepulse get networkpolicy
```

With the bundled broker enabled, expect runtime and MQTT pods.

Check runtime logs:

```bash
kubectl -n edgepulse logs deploy/edgepulse-runtime
```

Check broker logs:

```bash
kubectl -n edgepulse logs deploy/edgepulse-runtime-mqtt
```

## Check runtime readiness

Port-forward the runtime:

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime 8080:8080
```

In another terminal:

```bash
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/readyz | jq
curl -s http://localhost:8080/model/info | jq
```

The readiness response should report the current `0.9.0` model metadata and indicate whether MQTT is enabled.

## Test HTTP ingestion

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode http \
  --endpoint http://localhost:8080/infer \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Check metrics:

```bash
curl -s http://localhost:8080/metrics | grep 'ingestion="http"'
```

## Default MQTT mode

For backwards-compatible local Kubernetes testing, the chart's default secure-MQTT switches are disabled unless you enable them in values.

When using the default broker service port, port-forward it with:

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime-mqtt 1883:1883
```

If WSL already has a local service using port `1883`:

```bash
sudo ss -ltnp | grep ':1883' || true
sudo systemctl stop mosquitto || true
```

A plaintext simulator test can then use:

```bash
python3 -m simulators.vibration_sensor.simulate \
  --mode mqtt \
  --mqtt-host 127.0.0.1 \
  --mqtt-port 1883 \
  --count 5 \
  --interval-seconds 1 \
  --anomaly-rate 0.30
```

Verify:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
```

## Secure MQTT on Kubernetes

For a production-shaped secure deployment, enable broker authentication/TLS and runtime credentials/trust through existing Secrets.

The required secret responsibilities are:

```text
edgepulse-mqtt-passwords
  └── Mosquitto password file

edgepulse-mqtt-server-tls
  ├── tls.crt
  └── tls.key

edgepulse-runtime-mqtt-auth
  ├── username
  └── password

edgepulse-runtime-mqtt-ca
  └── ca.crt
```

Example values:

```yaml
mqtt:
  service:
    port: 8883

  auth:
    enabled: true
    existingSecret: edgepulse-mqtt-passwords

  tls:
    enabled: true
    existingSecret: edgepulse-mqtt-server-tls

runtime:
  mqtt:
    auth:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-auth

    tls:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-ca
```

Validate before installing:

```bash
helm lint charts/edgepulse-runtime
helm template edgepulse-runtime charts/edgepulse-runtime \
  -f secure-values.yaml > /tmp/edgepulse-secure.yaml
```

The chart does not issue certificates or generate production passwords. Use cert-manager, External Secrets, another cluster-standard mechanism, or development Secrets prepared before Helm installation.

See `charts/edgepulse-runtime/README.md` for the complete secure values interface.

## Optional ServiceMonitor

If Prometheus Operator is installed:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true
```

See `docs/servicemonitor.md`.

## Uninstall

```bash
helm uninstall edgepulse-runtime -n edgepulse
kubectl delete namespace edgepulse
```

## Delete the cluster

```bash
k3d cluster delete edgepulse
```
