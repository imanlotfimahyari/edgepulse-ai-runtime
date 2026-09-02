# EdgePulse Runtime Helm Chart

This chart deploys EdgePulse AI Runtime and, optionally, a Mosquitto MQTT broker.

Chart version and application version: **`0.9.0`**.

## Resources

Depending on values, the chart can render:

- EdgePulse Runtime Deployment and ClusterIP Service;
- Mosquitto Deployment and ClusterIP Service;
- Mosquitto configuration ConfigMap;
- ServiceAccount;
- NetworkPolicy;
- optional Prometheus Operator `ServiceMonitor`;
- mounts and environment references to existing Kubernetes Secrets for MQTT authentication and TLS.

## Validate the chart

```bash
helm lint charts/edgepulse-runtime
helm template edgepulse-runtime charts/edgepulse-runtime > /tmp/edgepulse-rendered.yaml
```

## Basic install

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace
```

The default runtime image is:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

Check the release:

```bash
kubectl -n edgepulse get pods -o wide
kubectl -n edgepulse get svc
```

## Local image with k3d

Build and import a local image:

```bash
docker build -t edgepulse-runtime:0.9.0 ./runtime
k3d image import edgepulse-runtime:0.9.0 -c edgepulse
```

Install with the local image:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.image.repository=edgepulse-runtime \
  --set runtime.image.tag=0.9.0 \
  --set runtime.image.pullPolicy=IfNotPresent
```

For a complete local Kubernetes walkthrough, see `docs/k3d-k3s-local.md`.

## Runtime configuration

The main runtime values include:

```yaml
runtime:
  replicaCount: 1

  image:
    repository: ghcr.io/imanlotfimahyari/edgepulse-runtime
    tag: "0.9.0"
    pullPolicy: IfNotPresent

  env:
    serviceName: edgepulse-ai-runtime
    modelName: edgepulse-anomaly-detector
    modelVersion: "0.9.0"
    modelBackend: rule-based
    modelPath: /app/models/anomaly_score.onnx
    anomalyThreshold: "0.65"
    mqttEnabled: "true"
    mqttTopic: edge/devices/+/telemetry
```

## Secure MQTT

The chart can configure both the runtime and the bundled broker to use existing Kubernetes Secrets.

The chart intentionally **does not generate production passwords, private keys, or certificates**. Supply them through your preferred platform mechanism, for example:

- cert-manager;
- an external PKI;
- External Secrets Operator;
- a cloud secret manager integration;
- manually created Kubernetes Secrets for development.

### Broker authentication

```yaml
mqtt:
  auth:
    enabled: true
    existingSecret: edgepulse-mqtt-passwords
    passwordFileKey: passwords
```

The referenced Secret must contain a Mosquitto-compatible password database under the configured key.

### Broker TLS

```yaml
mqtt:
  service:
    port: 8883

  tls:
    enabled: true
    existingSecret: edgepulse-mqtt-server-tls
    certKey: tls.crt
    keyKey: tls.key
```

When enabled, Mosquitto reads its certificate and private key from the referenced Secret.

### Runtime MQTT credentials

```yaml
runtime:
  mqtt:
    auth:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-auth
      usernameKey: username
      passwordKey: password
```

The Deployment injects the values through `secretKeyRef`; credentials are not rendered as literal Helm values in the Pod specification.

### Runtime broker trust

```yaml
runtime:
  mqtt:
    tls:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-ca
      caKey: ca.crt
```

The CA is mounted read-only and the runtime receives:

```text
MQTT_TLS_ENABLED=true
MQTT_TLS_CA_FILE=/etc/edgepulse/mqtt-tls/ca.crt
```

### Optional client certificate

EdgePulse can also present a client certificate when connecting to an external mTLS-enabled broker:

```yaml
runtime:
  mqtt:
    tls:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-client
      caKey: ca.crt

      clientCertificate:
        enabled: true
        certKey: tls.crt
        keyKey: tls.key
```

This mounts the client certificate and key and configures:

```text
MQTT_TLS_CERT_FILE=/etc/edgepulse/mqtt-tls/tls.crt
MQTT_TLS_KEY_FILE=/etc/edgepulse/mqtt-tls/tls.key
```

The bundled broker configuration does not require client certificates by default. Client-certificate support exists so the runtime can connect to a broker that enforces mTLS.

## Example secure values

```yaml
mqtt:
  service:
    port: 8883

  auth:
    enabled: true
    existingSecret: edgepulse-mqtt-passwords
    passwordFileKey: passwords

  tls:
    enabled: true
    existingSecret: edgepulse-mqtt-server-tls
    certKey: tls.crt
    keyKey: tls.key

runtime:
  mqtt:
    auth:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-auth
      usernameKey: username
      passwordKey: password

    tls:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-ca
      caKey: ca.crt
```

Render it before installation:

```bash
helm template edgepulse-runtime charts/edgepulse-runtime \
  -f secure-values.yaml > /tmp/edgepulse-secure.yaml
```

Useful validation:

```bash
grep -nE \
  'MQTT_USERNAME|MQTT_PASSWORD|MQTT_TLS|password_file|allow_anonymous|certfile|keyfile|secretName|8883' \
  /tmp/edgepulse-secure.yaml
```

## ServiceMonitor

`ServiceMonitor` creation is disabled by default because the CRD is not present in every cluster:

```yaml
serviceMonitor:
  enabled: false
```

Enable it when Prometheus Operator is installed:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true
```

For kube-prometheus-stack installations that select ServiceMonitors by label:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true \
  --set serviceMonitor.labels.release=kube-prometheus-stack
```

See `docs/servicemonitor.md` for details.

## Probes and runtime health

The chart uses:

- `/healthz` for liveness;
- `/readyz` for readiness.

When MQTT is enabled, runtime readiness requires an active MQTT connection. This prevents Kubernetes from treating an MQTT-dependent instance as ready when its broker connection is unavailable.

## Security defaults

The chart includes production-oriented pod/container defaults such as:

- non-root execution;
- dropped capabilities;
- disabled privilege escalation;
- read-only root filesystem;
- disabled automatic ServiceAccount token mounting;
- `RuntimeDefault` seccomp;
- resource requests and limits;
- NetworkPolicy support.

See `docs/security.md` for the broader security model.
