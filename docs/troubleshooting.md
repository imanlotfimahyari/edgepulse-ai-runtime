# Troubleshooting

This guide focuses on the current runtime, secured Docker Compose environment, MQTT dependency behavior, and Helm/Kubernetes deployment.

## Start with state and logs

For Docker Compose:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  ps -a
```

Runtime logs:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  logs --tail=100 edgepulse-runtime
```

Broker logs:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  logs --tail=100 mqtt
```

Healthy secured startup should show the runtime MQTT client connecting successfully and the broker reporting a TLS-authenticated client.

## `/healthz` is 200 but `/readyz` is not ready

This can be expected.

```text
/healthz = process liveness
/readyz  = runtime dependency readiness
```

When MQTT is enabled, `/readyz` requires an active broker connection.

Check:

```bash
curl -i http://localhost:8080/healthz
curl -i http://localhost:8080/readyz
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_connected
```

Then inspect runtime and broker logs for connection, TLS, or authentication errors.

## TLS certificate verification fails in Compose

Typical error:

```text
ssl.SSLCertVerificationError:
certificate verify failed: unable to get local issuer certificate
```

The Compose environment stores generated test PKI in the `mqtt-security` volume. If that volume is changed while a running broker still has an older certificate loaded, clients can see a CA/server-certificate mismatch.

Reset the complete local security state:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  down -v --remove-orphans
```

Confirm no stale security volume remains:

```bash
docker volume ls | grep mqtt-security || true
```

Restart:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  up -d --build mqtt edgepulse-runtime
```

Then run E2E without restarting dependencies:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  run --rm --no-deps --build e2e
```

`--no-deps` is important because the broker/runtime stack is already running and the E2E service is intended to be a one-off test client.

## Security-init exits with code 0

That is normal. `mqtt-security-init` is intentionally a one-shot service.

Expected Compose state:

```text
mqtt-security-init   Exited (0)
edgepulse-mqtt       Up
edgepulse-runtime    Up (healthy)
```

Do not use a Compose mode that aborts the stack merely because the successful init container exits.

## MQTT authentication fails

Broker logs may show refused or unauthorized clients.

Check that the runtime has authentication enabled without exposing the password:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  logs edgepulse-runtime | grep 'tls=.*auth='
```

Expected secured Compose startup includes:

```text
tls=True auth=True
```

Then check broker logs for the client username.

## MQTT E2E does not process a message

Confirm broker connectivity first:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_connected
```

Expected while connected:

```text
edgepulse_mqtt_connected 1.0
```

Run the E2E service:

```bash
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  --profile e2e \
  run --rm --no-deps --build e2e
```

Then inspect:

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
```

## Port 8883 or 8080 is already in use

Check host listeners:

```bash
sudo ss -ltnp | grep -E ':8080|:8883' || true
```

Stop the conflicting process or change the host-side Compose port mapping.

For the default plaintext Helm/k3d broker workflow, check port `1883` instead.

## Docker cannot pull Mosquitto or Python base images

Check Docker Desktop connectivity, proxy, DNS, and registry access:

```bash
docker pull eclipse-mosquitto:2
docker pull python:3.12-slim
```

If these fail independently of Compose, troubleshoot Docker/registry networking first.

## Runtime cannot start in ONNX mode

Check:

```text
MODEL_BACKEND=onnx
MODEL_PATH=/app/models/anomaly_score.onnx
```

Inspect runtime startup logs. A model initialization problem should make readiness fail rather than silently accepting traffic.

## Helm rendering fails when secure MQTT is enabled

Secure chart values require existing Secret names.

For example, enabling runtime TLS without `runtime.mqtt.tls.existingSecret` should fail template rendering intentionally.

Render locally:

```bash
helm lint charts/edgepulse-runtime
helm template edgepulse-runtime charts/edgepulse-runtime \
  -f secure-values.yaml > /tmp/edgepulse-secure.yaml
```

Inspect Secret references:

```bash
grep -n 'secretName:' /tmp/edgepulse-secure.yaml
```

## Kubernetes Pod is not ready

Check:

```bash
kubectl -n edgepulse get pods
kubectl -n edgepulse describe pod <pod-name>
kubectl -n edgepulse logs deploy/edgepulse-runtime
```

If MQTT is enabled, also inspect the broker Pod and Service:

```bash
kubectl -n edgepulse get svc
kubectl -n edgepulse logs deploy/edgepulse-runtime-mqtt
```

For secure mode, verify referenced Secrets exist:

```bash
kubectl -n edgepulse get secret
```

## ServiceMonitor exists but there are no metrics

See `docs/servicemonitor.md`. Most failures are one of:

- Prometheus Operator CRD not installed;
- Prometheus selector labels do not match the ServiceMonitor;
- Service port/path mismatch;
- runtime itself is not reachable.

## Pre-commit modifies files

Some hooks, including Ruff formatting/fixes, can update files.

After running:

```bash
pre-commit run --all-files
```

always inspect:

```bash
git status
git diff
```

Then rerun pre-commit until all hooks pass without further modifications.
