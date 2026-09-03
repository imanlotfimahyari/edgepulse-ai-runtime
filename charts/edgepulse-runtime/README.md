# EdgePulse Runtime Helm Chart

This chart deploys EdgePulse AI Runtime and, optionally, a Mosquitto MQTT broker.

Chart version and application version: **`0.9.0`**.

## Resources

Depending on values, the chart can render:

* EdgePulse Runtime Deployment and ClusterIP Service;
* Mosquitto Deployment and ClusterIP Service;
* Mosquitto configuration ConfigMap;
* ServiceAccount;
* NetworkPolicy;
* optional Prometheus Operator `ServiceMonitor`;
* mounts and environment references to existing Kubernetes Secrets for MQTT authentication and TLS.

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
    executionProfile: balanced
    modelPath: /app/models/anomaly_score.onnx
    anomalyThreshold: "0.65"
    mqttEnabled: "true"
    mqttTopic: edge/devices/+/telemetry
```

## ONNX execution profile

When the ONNX backend is selected, the chart can configure the runtime execution policy through:

```yaml
runtime:
  env:
    modelBackend: onnx
    executionProfile: eco
```

Supported execution profiles:

```text
eco
balanced
```

`eco` uses a single ONNX intra-op thread with thread spinning disabled.

`balanced` uses ONNX Runtime automatic intra-op threading with thread spinning enabled.

The default is:

```text
balanced
```

Example install:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco
```

Verify the deployed configuration:

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime 8080:8080
```

Then:

```bash
curl -s http://localhost:8080/model/info | jq
```

Execution profiles affect only ONNX inference. They are exposed through `/model/info` so the effective runtime policy can be observed and associated with benchmark results.

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

## Secure MQTT

The chart can configure both the runtime and the bundled broker to use existing Kubernetes Secrets.

The chart intentionally **does not generate production passwords, private keys, or certificates**.

Supply them through your preferred platform mechanism, for example:

* cert-manager;
* an external PKI;
* External Secrets Operator;
* a cloud secret manager integration;
* manually created Kubernetes Secrets for development.

### Broker authentication

```yaml
mqtt:
  auth:
    enabled: true
    existingSecret: edgepulse-mqtt-passwords
    passwordFileKey: passwords
```

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

The Deployment injects credentials through `secretKeyRef`; credentials are not rendered as literal Helm values in the Pod specification.

### Runtime broker trust

```yaml
runtime:
  mqtt:
    tls:
      enabled: true
      existingSecret: edgepulse-runtime-mqtt-ca
      caKey: ca.crt
```

The runtime receives:

```text
MQTT_TLS_ENABLED=true
MQTT_TLS_CA_FILE=/etc/edgepulse/mqtt-tls/ca.crt
```

### Optional client certificate

EdgePulse can present a client certificate when connecting to an external mTLS-enabled broker:

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

This configures:

```text
MQTT_TLS_CERT_FILE=/etc/edgepulse/mqtt-tls/tls.crt
MQTT_TLS_KEY_FILE=/etc/edgepulse/mqtt-tls/tls.key
```

The bundled broker does not require client certificates by default.

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
  env:
    modelBackend: onnx
    executionProfile: eco

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

## ServiceMonitor

`ServiceMonitor` creation is disabled by default:

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

See `docs/servicemonitor.md` for details.

## Probes and runtime health

The chart uses:

* `/healthz` for liveness;
* `/readyz` for readiness.

When MQTT is enabled, runtime readiness requires an active MQTT connection.

## Resource defaults

The runtime has default requests and limits:

```yaml
runtime:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

These Kubernetes resource limits are independent from `executionProfile`.

```text
Kubernetes resources
    -> how much CPU/memory the container receives

executionProfile
    -> how ONNX Runtime uses the available compute
```

This distinction is intentional.

## Security defaults

The chart includes:

* non-root execution;
* dropped capabilities;
* disabled privilege escalation;
* read-only root filesystem;
* disabled automatic ServiceAccount token mounting;
* `RuntimeDefault` seccomp;
* resource requests and limits;
* NetworkPolicy support.

See `docs/security.md` for the broader security model.
