# EdgePulse Top

`edgepulse-top` is the node-local operational terminal interface for EdgePulse AI Runtime.

It provides immediate visibility into one running EdgePulse instance without introducing a second observability system.

The implementation is located at:

```text
scripts/edgepulse_top.py
```

## Purpose

The project has three complementary observability and performance interfaces:

```text
EdgePulse Runtime
       |
       +---- /healthz
       +---- /readyz
       +---- /model/info
       +---- /metrics
              |
              +-----------> edgepulse-top
              |             immediate node-local state
              |
              +-----------> Prometheus / Grafana
              |             historical / fleet visibility
              |
              +-----------> benchmark_runtime.py
                            controlled performance experiments
```

`edgepulse-top` consumes the same APIs and Prometheus telemetry already used elsewhere in the platform.

It does not create a separate metrics model.

## Tool dependency

The runtime container does not require a terminal UI library.

Local operational-tool dependencies are kept separately:

```text
requirements-tools.txt
```

Install them with:

```bash
pip install -r requirements-tools.txt
```

The live interface uses Rich for terminal rendering.

## Running the dashboard

From the development container:

```bash
python scripts/edgepulse_top.py
```

The default runtime endpoint is:

```text
http://host.docker.internal:8080
```

Specify another endpoint with:

```bash
python scripts/edgepulse_top.py \
  --base-url http://edge-node:8080
```

Change the sampling interval:

```bash
python scripts/edgepulse_top.py \
  --interval 1
```

The default is:

```text
2 seconds
```

## Single-snapshot modes

Human-readable output:

```bash
python scripts/edgepulse_top.py --once
```

Machine-readable JSON:

```bash
python scripts/edgepulse_top.py --json
```

These modes are useful for:

* shell scripts;
* automated diagnostics;
* tests;
* environments where a live TTY is unavailable.

## Dashboard structure

The live view contains:

```text
EdgePulse Top
    |
    +-- runtime status
    |
    +-- model state
    |
    +-- resource budget
    |
    +-- inference state
    |
    +-- MQTT state
    |
    +-- rolling trends
    |
    +-- inference latency
```

A typical dashboard contains:

```text
╭──────────────────────── EdgePulse Top ────────────────────────╮
│ ● READY       ● MQTT CONNECTED       ● LIVE      refresh 2.0s │
╰───────────────────────────────────────────────────────────────╯

╭─ Runtime ─────────────────╮ ╭─ Model ────────────────────────╮
│ Service      edgepulse... │ │ Model      anomaly-detector   │
│ Version      0.9.0        │ │ Backend    ONNX               │
│ Health       ● OK         │ │ Profile    eco (active)       │
│ Readiness    ● READY      │ │ Artifact   270 B              │
╰───────────────────────────╯ ╰───────────────────────────────╯

╭─ Resources ──────────────────────────────────────────────────╮
│ CPU       97.0%  ███████████████████░  0.485 / 0.500 cores  │
│ Memory    12.0%  ██░░░░░░░░░░░░░░░░░  61.4 / 512 MiB      │
│ Headroom                                  450.6 MiB           │
╰──────────────────────────────────────────────────────────────╯

╭─ Inference ───────────────╮ ╭─ MQTT ─────────────────────────╮
│ Rate          490.0/s    │ │ State          ● CONNECTED     │
│ Concurrency   2          │ │ Rate           8.0/s           │
│ Errors        0.0/s      │ │ Errors         0.0/s           │
╰───────────────────────────╯ ╰───────────────────────────────╯

╭─ Recent trend · 30 samples ──────────────────────────────────╮
│ CPU       ▁▁▂▄▇████████▆▄▂▁                 97.0%            │
│ Infer/s   ▁▁▂▄▇████████▆▄▂▁                 490.0/s          │
╰──────────────────────────────────────────────────────────────╯

╭─ Inference latency ──────────────────────────────────────────╮
│             p50              p95              p99             │
│           0.150 ms         0.410 ms         0.810 ms         │
╰──────────────────────────────────────────────────────────────╯
```

## Runtime state

Runtime state comes from:

```text
GET /healthz
GET /readyz
```

The dashboard exposes:

```text
Health
Readiness
```

Readiness includes dependency state such as MQTT connectivity when MQTT is enabled.

## Model state

Model information comes from:

```text
GET /model/info
```

The dashboard displays:

* model name;
* model version;
* inference backend;
* execution profile;
* whether the execution profile is active;
* model artifact size.

The artifact size is sourced from:

```text
edgepulse_model_artifact_size_bytes
```

This becomes particularly useful when comparing future FP32 and quantized model artifacts.

## MQTT state

MQTT connection state comes from:

```text
edgepulse_mqtt_connected
```

Traffic rates are calculated from:

```text
edgepulse_mqtt_messages_total
edgepulse_mqtt_errors_total
```

A connection state of:

```text
1
```

is displayed as:

```text
CONNECTED
```

A connection state of:

```text
0
```

is displayed as:

```text
DISCONNECTED
```

## Resource state

CPU and memory values come from the same cgroup-aware telemetry already exposed by EdgePulse.

### CPU budget

The CPU budget comes from:

```text
edgepulse_resource_cpu_limit_cores
```

Live CPU consumption is calculated from successive samples of:

```text
process_cpu_seconds_total
```

For two samples:

```text
CPU cores used
    =
delta process_cpu_seconds_total
--------------------------------
delta wall-clock time
```

CPU-budget utilization is:

```text
CPU cores used
----------------------
configured CPU quota
```

For example:

```text
CPU used:    0.485 cores
CPU budget:  0.500 cores

utilization:
0.485 / 0.500 = 97%
```

### CPU status colors

High CPU consumption does not automatically mean the runtime is unhealthy.

For controlled inference workloads, consuming most of the available CPU quota can be expected.

The TUI therefore uses:

```text
< 85%       green
85–100%     yellow
>= 100%     red
```

Yellow means:

```text
busy / near configured capacity
```

rather than:

```text
runtime failure
```

Measurements slightly above 100% can occur because process CPU accounting and polling intervals are not perfectly synchronized.

### Memory

Memory state uses:

```text
edgepulse_resource_memory_current_bytes
edgepulse_resource_memory_limit_bytes
edgepulse_resource_memory_headroom_bytes
edgepulse_resource_memory_utilization_ratio
```

Memory uses more conservative status thresholds:

```text
< 75%       green
75–90%      yellow
>= 90%      red
```

Memory exhaustion is more dangerous because exceeding the container's memory limit can result in OOM termination.

## Live rates

Prometheus counters are cumulative.

`edgepulse-top` calculates live rates by comparing successive snapshots.

For a counter:

```text
rate
    =
current counter - previous counter
----------------------------------
elapsed seconds
```

This is used for:

```text
inference requests / second
inference errors / second
MQTT messages / second
MQTT errors / second
```

Counter resets are detected.

If:

```text
current counter < previous counter
```

the derived rate is treated as unavailable for that interval.

This prevents a runtime restart from generating a false negative rate.

## Inference latency

The runtime exports:

```text
edgepulse_inference_latency_seconds
```

as a Prometheus histogram.

The histogram uses explicit low-latency buckets because the current lightweight inference workload can complete in sub-millisecond time.

`edgepulse-top` compares cumulative histogram buckets between two snapshots.

The delta represents observations occurring during that sampling interval.

Percentiles are then estimated from the bucket distribution:

```text
p50
p95
p99
```

These are **histogram estimates**, not exact request-level percentiles.

This is different from `benchmark_runtime.py`, which records individual request timings and calculates percentiles directly.

The two therefore have different purposes:

```text
edgepulse-top
    -> live operational estimate

benchmark_runtime.py
    -> controlled experiment-level measurement
```

When no inference occurred during the sampling interval, latency is shown as:

```text
n/a
```

rather than carrying forward stale latency values.

## Rolling trends

`edgepulse-top` maintains a small in-memory history of the most recent samples.

The default history contains:

```text
30 samples
```

At the default two-second polling interval this represents approximately:

```text
60 seconds
```

Two sparklines are displayed:

```text
CPU
Infer/s
```

Example:

```text
CPU       ▁▁▂▃▆████▇▆▃▂▁
Infer/s   ▁▁▂▄▇█████▆▃▁▁
```

The trend is intentionally lightweight.

It provides immediate visual context for transitions such as:

```text
idle
  |
load begins
  |
CPU saturation
  |
load ends
  |
idle
```

Historical analysis remains the responsibility of Prometheus and Grafana.

## Telemetry state

Collecting one dashboard sample requires several runtime requests:

```text
/healthz
/readyz
/model/info
/metrics
```

A transient request failure should not immediately erase the last known operational state.

The TUI therefore tracks its own telemetry status.

### Live

```text
● LIVE
```

The latest polling cycle succeeded.

### Degraded

```text
● DEGRADED
```

One or two consecutive polling cycles failed.

The last successful dashboard remains visible.

This distinguishes a temporary scrape or network problem from confirmed runtime failure.

### Unreachable

After repeated consecutive failures:

```text
● UNREACHABLE
```

is displayed.

The last-known state remains visible where available, together with the polling error.

When polling succeeds again, status automatically returns to:

```text
● LIVE
```

## Why not mark every component healthy?

The dashboard intentionally avoids inventing health states without defined operational semantics.

For example, the following questions require actual policy:

```text
Is 97% CPU unhealthy?

Is 10 ms p95 latency unhealthy?

Is 0.1% inference error rate unhealthy?
```

Those answers require:

* SLOs;
* capacity thresholds;
* latency targets;
* error budgets.

Until those exist, `edgepulse-top` displays measured state rather than arbitrary green/red judgments.

Statuses are used only where the meaning is already objective:

```text
runtime liveness
runtime readiness
MQTT connection
telemetry scrape state
execution profile active/inactive
```

A future SLO-oriented increment can add semantic service-health states once those thresholds are formally defined.

## Testing under load

Start EdgePulse:

```bash
MODEL_BACKEND=onnx \
EXECUTION_PROFILE=eco \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build --force-recreate edgepulse-runtime
```

Start the TUI:

```bash
python scripts/edgepulse_top.py
```

In another terminal run:

```bash
python scripts/benchmark_runtime.py \
  --duration 30 \
  --warmup 2 \
  --concurrency 2
```

The dashboard should show:

```text
CPU
    idle -> near CPU quota -> idle

Inference rate
    0 -> hundreds/sec -> 0

Latency
    n/a -> populated -> n/a

Memory
    comparatively stable
```

This provides a direct visual demonstration of resource saturation and recovery under a controlled inference workload.

## Scope

`edgepulse-top` is intentionally not:

* a replacement for Prometheus;
* a replacement for Grafana;
* a fleet-management UI;
* a historical time-series database;
* an alert manager;
* a full-screen device-management application.

Its role is deliberately narrow:

> provide useful immediate state directly on an edge node or engineering terminal.
