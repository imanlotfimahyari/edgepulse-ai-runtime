# ServiceMonitor Support

The Helm chart can optionally create a `ServiceMonitor` for Prometheus Operator based monitoring.

This is disabled by default because not every Kubernetes cluster has the Prometheus Operator CRDs installed.

## Enable ServiceMonitor

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true
```

## Enable with kube-prometheus-stack labels

Some kube-prometheus-stack installations select ServiceMonitors by label.

Example:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true \
  --set serviceMonitor.labels.release=kube-prometheus-stack
```

## Render locally

```bash
helm template edgepulse-runtime charts/edgepulse-runtime \
  --set serviceMonitor.enabled=true
```

Expected resource:

```text
kind: ServiceMonitor
```

## Metrics endpoint

The ServiceMonitor scrapes:

```text
/metrics
```

on the runtime Service port:

```text
http
```

## Notes

The ServiceMonitor requires the Prometheus Operator CRD:

```text
monitoring.coreos.com/v1 ServiceMonitor
```

If the CRD is not installed, keep `serviceMonitor.enabled=false`.
