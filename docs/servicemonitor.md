# ServiceMonitor Support

The Helm chart can optionally create a Prometheus Operator `ServiceMonitor` for the EdgePulse runtime.

It is disabled by default because the `ServiceMonitor` CRD is not installed in every Kubernetes cluster.

## Enable it

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true
```

Render before installing:

```bash
helm template edgepulse-runtime charts/edgepulse-runtime \
  --set serviceMonitor.enabled=true \
  > /tmp/edgepulse-servicemonitor.yaml
```

Confirm:

```bash
grep -n 'kind: ServiceMonitor' /tmp/edgepulse-servicemonitor.yaml
```

## Default scrape behavior

The ServiceMonitor scrapes:

```text
path: /metrics
runtime Service port: http
```

Default chart values include:

```yaml
serviceMonitor:
  enabled: false
  interval: 30s
  scrapeTimeout: 10s
  labels: {}
  annotations: {}
  metricRelabelings: []
  relabelings: []
```

## kube-prometheus-stack selector labels

Prometheus Operator installations often select ServiceMonitors using labels.

For example:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set serviceMonitor.enabled=true \
  --set serviceMonitor.labels.release=kube-prometheus-stack
```

Use the label expected by your Prometheus resource; the exact selector is cluster-specific.

## Requirements

The cluster must have the CRD:

```text
monitoring.coreos.com/v1
kind: ServiceMonitor
```

Check:

```bash
kubectl get crd servicemonitors.monitoring.coreos.com
```

If it is not installed, leave:

```yaml
serviceMonitor:
  enabled: false
```

## Troubleshooting

If the ServiceMonitor exists but Prometheus does not scrape EdgePulse:

1. inspect the ServiceMonitor:

```bash
kubectl -n edgepulse get servicemonitor -o yaml
```

2. confirm the runtime Service exposes the named `http` port:

```bash
kubectl -n edgepulse get svc edgepulse-runtime -o yaml
```

3. confirm the Prometheus resource selects the ServiceMonitor labels;
4. verify the runtime `/metrics` endpoint directly with a port-forward.

```bash
kubectl -n edgepulse port-forward svc/edgepulse-runtime 8080:8080
curl -s http://localhost:8080/metrics | head
```

See `docs/observability.md` for metric and PromQL examples.
