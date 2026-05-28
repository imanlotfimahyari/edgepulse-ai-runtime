# EdgePulse Runtime Helm Chart

This chart deploys EdgePulse AI Runtime and an optional Mosquitto MQTT broker.

## Components

The chart deploys:

- EdgePulse AI Runtime Deployment
- EdgePulse Runtime ClusterIP Service
- Mosquitto Deployment
- Mosquitto ClusterIP Service
- Mosquitto ConfigMap

## Lint

```bash
helm lint charts/edgepulse-runtime
```

## Render templates

```bash
helm template edgepulse-runtime charts/edgepulse-runtime
```

## Install

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.image.repository=edgepulse-runtime \
  --set runtime.image.tag=0.2.0 \
  --set runtime.image.pullPolicy=IfNotPresent
```

## Check resources

```bash
kubectl -n edgepulse get all
kubectl -n edgepulse get pods -o wide
```

## Port-forward runtime

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime 8080:8080
```

## Port-forward MQTT broker

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime-mqtt 1883:1883
```

## Local image note

For k3d, build and import the image before installing the chart:

```bash
docker build -t edgepulse-runtime:0.2.0 ./runtime
k3d image import edgepulse-runtime:0.2.0 -c edgepulse
```

For a remote Kubernetes cluster, push the image to a registry accessible by the cluster and override:

```bash
--set runtime.image.repository=<registry>/edgepulse-runtime
--set runtime.image.tag=<tag>
```

## ServiceMonitor

The chart can optionally create a Prometheus Operator `ServiceMonitor`.

It is disabled by default:

```yaml
serviceMonitor:
  enabled: false
```

Enable it when the Prometheus Operator CRDs are installed:

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
