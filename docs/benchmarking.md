# Runtime Benchmarking

EdgePulse includes a lightweight benchmark client for measuring inference performance and resource efficiency under constrained edge-runtime budgets.

The benchmark is implemented with the Python standard library so it can run without requiring a separate load-testing framework.

The objective is not only to measure maximum requests per second. The benchmark is designed to show how much useful inference work the runtime can perform for a given CPU and memory budget, how latency changes as concurrency approaches saturation, and how ONNX Runtime execution strategies affect constrained edge workloads.

## Benchmark client

The benchmark client is located at:

```text
scripts/benchmark_runtime.py
```

It sends HTTP inference requests to the runtime, samples runtime resource metrics, reads model/execution metadata, and optionally writes the result to a machine-readable JSON file.

## What is measured

The benchmark records:

* successful requests;
* request errors;
* request throughput;
* client end-to-end latency;
* EdgePulse inference latency;
* process CPU consumption;
* configured cgroup CPU quota;
* CPU-budget utilization;
* average memory observed during the benchmark;
* maximum memory observed during the benchmark;
* cgroup lifetime peak memory;
* configured cgroup memory budget;
* remaining memory headroom;
* successful inferences per CPU-second;
* model backend;
* active execution-profile metadata.

Latency is reported as p50, p95, p99, and mean values where applicable.

## Client latency versus inference latency

The benchmark deliberately records two latency measurements.

```text
benchmark client
       |
       | client end-to-end latency
       v
   POST /infer
       |
       | runtime inference latency
       v
 inference backend
```

Client latency includes work such as:

* HTTP request and response handling;
* serialization and deserialization;
* process scheduling;
* request queuing;
* inference execution.

Inference latency is the latency measured by EdgePulse around the inference operation itself.

The distinction is useful when diagnosing saturation. A runtime can have a very fast inference function while still experiencing high client tail latency because requests are waiting for CPU time or server processing.

## Resource measurements

The benchmark consumes the Prometheus metrics exposed by EdgePulse.

### CPU

Process CPU consumption is calculated from the difference in:

```promql
process_cpu_seconds_total
```

before and after the measured workload.

Average CPU consumption is expressed in cores:

```text
CPU seconds consumed
--------------------
benchmark wall time
```

The configured CPU budget comes from:

```promql
edgepulse_resource_cpu_limit_cores
```

CPU-budget utilization is then calculated as:

```text
average CPU cores used
----------------------
configured CPU cores
```

Values around 100% indicate that the workload is effectively consuming the available CPU quota.

Small measurements slightly above 100% can occur because process CPU accounting and wall-clock sampling do not share perfectly aligned boundaries.

### Memory

Memory is sampled periodically during the measured workload using:

```promql
edgepulse_resource_memory_current_bytes
```

This produces two benchmark-specific values:

```text
memory_average_bytes
memory_max_observed_bytes
```

These are preferable for comparing individual benchmark runs because:

```promql
edgepulse_resource_memory_peak_bytes
```

represents the cgroup lifetime peak and therefore does not reset between benchmark executions.

The benchmark still records the cgroup lifetime peak as additional diagnostic information.

## Efficiency

EdgePulse also calculates:

```text
inferences_per_cpu_second
```

This is:

```text
successful inference requests
-----------------------------
process CPU seconds consumed
```

It provides a simple measure of how much inference work was completed for the CPU consumed.

This metric is useful when comparing:

* inference backends;
* CPU budgets;
* runtime execution profiles;
* model optimizations;
* model quantization.

## Running a benchmark

Start a healthy EdgePulse runtime first.

From the development container:

```bash
python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 2 \
  --output /tmp/edgepulse-benchmark.json
```

The default runtime endpoint is:

```text
http://host.docker.internal:8080
```

A different runtime can be selected with:

```bash
python scripts/benchmark_runtime.py \
  --base-url http://edge-node:8080 \
  --duration 20 \
  --warmup 2 \
  --concurrency 2
```

## Benchmark parameters

| Option          | Purpose                                       |
| --------------- | --------------------------------------------- |
| `--base-url`    | EdgePulse HTTP endpoint.                      |
| `--duration`    | Duration of the measured workload in seconds. |
| `--warmup`      | Warm-up duration before measurements begin.   |
| `--concurrency` | Number of concurrent benchmark workers.       |
| `--timeout`     | HTTP request timeout.                         |
| `--output`      | Optional JSON result path.                    |

## Concurrency sweep

A useful capacity experiment is to execute the same workload at increasing concurrency:

```bash
python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 1 \
  --output /tmp/edgepulse-c1.json

python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 2 \
  --output /tmp/edgepulse-c2.json

python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 4 \
  --output /tmp/edgepulse-c4.json

python scripts/benchmark_runtime.py \
  --duration 20 \
  --warmup 2 \
  --concurrency 8 \
  --output /tmp/edgepulse-c8.json
```

The objective is to find the useful operating region rather than simply the largest request-rate number.

A useful operating point balances:

* throughput;
* p95 and p99 latency;
* CPU-budget utilization;
* memory consumption;
* request errors;
* inference efficiency.

When throughput improves only slightly while tail latency rises sharply, the runtime has entered its saturation region.

## Repeatability

Short performance runs can be affected by:

* host scheduling;
* Docker scheduling;
* CPU frequency changes;
* background processes;
* runtime warm-up;
* filesystem activity;
* other workloads on the development machine.

For comparative experiments, run every workload multiple times.

The EdgePulse validation matrices use:

```text
duration:     20 seconds
warm-up:      2 seconds
repetitions:  3 where available
concurrency:  1, 2, 4, 8
CPU budget:   0.5 core
memory limit: 512 MiB
```

Median values across repeated runs are more useful than treating one short benchmark as an absolute result.

## Initial constrained-runtime experiment

The initial benchmark experiment compared the rule-based and ONNX backends using the same Compose resource budget:

```text
CPU:     0.5 core
Memory:  512 MiB
```

Repeated measurements showed a consistent saturation pattern.

At concurrency 2, both backends were already using approximately the available 0.5-core CPU budget while maintaining relatively low client p95 latency.

Increasing concurrency to 4 and 8 provided only limited additional throughput while client p95 latency increased substantially.

The practical conclusion for this workload was:

> Under the 0.5-core test budget, concurrency 2 is a useful low-latency operating point. Higher concurrency can extract some additional throughput, but at a disproportionate tail-latency cost.

The experiment also showed that memory was not the limiting resource for the current workload.

## Rule-based versus ONNX

The ONNX backend requires more inference work than the simple rule-based backend.

Under the same constrained runtime budget, repeated measurements showed that:

* ONNX generally produced lower throughput than the rule-based backend;
* ONNX inference latency was higher;
* ONNX completed fewer inferences per CPU-second;
* both backends became CPU constrained before memory constrained.

These results apply only to the current EdgePulse demo workload.

The packaged ONNX artifact is intentionally tiny:

```text
models/anomaly_score.onnx
```

Its artifact size is approximately:

```text
270 bytes
```

The results must therefore not be interpreted as general ONNX Runtime performance characteristics or as representative of production ML models.

## Execution-profile experiment

EdgePulse supports two ONNX execution profiles:

```text
eco
balanced
```

### Eco

```text
intra-op threads: 1
execution mode:   sequential
thread spinning:  disabled
```

The goal is a simple execution policy for a highly constrained edge CPU.

### Balanced

```text
intra-op threads: ONNX Runtime automatic
execution mode:   sequential
thread spinning:  enabled
```

This represents the general-purpose ONNX Runtime automatic-threading baseline.

### Why only two profiles?

Profile definitions were selected experimentally rather than by naming configuration combinations in advance.

An early `performance` candidate enabled parallel graph execution. Under the 0.5-core test quota and the current tiny ONNX graph, that configuration was dramatically slower and was rejected.

A later single-threaded spinning candidate was tested as a potential `latency` profile. Repeated measurements did not show a consistent latency advantage over `eco`, so it was also removed.

The final public profiles therefore represent configurations with defensible, distinct purposes rather than preserving profile names that the benchmark evidence did not support.

## Final execution-profile observations

A repeated ONNX profile matrix was run across concurrency levels 1, 2, 4, and 8 under:

```text
CPU:     0.5 core
Memory:  512 MiB
```

Representative median results from the final matrix included:

| Profile    | Concurrency | Throughput req/s | Client p95 | Inference p95 | CPU budget | Avg memory | Infer/CPU-s |
| ---------- | ----------: | ---------------: | ---------: | ------------: | ---------: | ---------: | ----------: |
| `eco`      |           1 |           486.80 |   2.387 ms |      0.123 ms |      87.5% |   59.3 MiB |     1130.89 |
| `eco`      |           2 |           480.32 |   4.441 ms |      0.414 ms |      97.2% |   59.2 MiB |      985.60 |
| `eco`      |           4 |           515.47 |  47.953 ms |      0.737 ms |      97.3% |   59.7 MiB |     1041.01 |
| `eco`      |           8 |           519.04 |  62.259 ms |      1.110 ms |      99.2% |   60.4 MiB |     1056.79 |
| `balanced` |           1 |           456.77 |   2.603 ms |      0.134 ms |      87.7% |   59.9 MiB |     1041.07 |
| `balanced` |           2 |           491.70 |   4.594 ms |      0.398 ms |      97.9% |   60.1 MiB |     1005.36 |
| `balanced` |           4 |           495.75 |  48.310 ms |      0.768 ms |      97.2% |   60.3 MiB |     1020.16 |
| `balanced` |           8 |           503.29 |  62.661 ms |      1.114 ms |      97.4% |   60.9 MiB |     1018.28 |

These results demonstrate an important edge-runtime point:

> More inference threads are not automatically better when the container has significantly less than one CPU core available.

For the current small model, `eco` frequently improved throughput and inferences per CPU-second while using a simpler execution model.

`balanced` remains useful as the general-purpose/default ONNX Runtime execution strategy and may become preferable as model complexity or the available CPU budget increases.

The results should therefore be understood as workload- and resource-envelope-specific evidence rather than universal ONNX tuning guidance.

## Selecting a profile

Docker Compose:

```bash
MODEL_BACKEND=onnx \
EXECUTION_PROFILE=eco \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build --force-recreate edgepulse-runtime
```

Kubernetes/Helm:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco
```

Verify the effective configuration:

```bash
curl -s http://localhost:8080/model/info | jq
```

## JSON output

When `--output` is specified, the benchmark writes machine-readable JSON.

The top-level sections are:

```text
runtime
workload
client_latency_ms
inference_latency_ms
resources
efficiency
```

The runtime section includes execution-profile metadata so benchmark results remain traceable to the exact runtime policy that produced them.

Example comparison dimensions include:

```text
rule-based vs ONNX
eco vs balanced
concurrency 1 vs 2 vs 4 vs 8
different CPU budgets
different memory budgets
FP32 vs quantized models
different ONNX Runtime configurations
```

Benchmark result files produced during ad-hoc validation normally remain outside the repository unless a particular result is intentionally preserved as a documented reference experiment.

## Benchmarking versus monitoring

Benchmarking and runtime monitoring serve different purposes.

```text
Benchmark client
    |
    +--> generates controlled workload
    |
    +--> calculates experiment-level results

Prometheus / Grafana
    |
    +--> observes runtime behavior continuously
    |
    +--> provides historical operational visibility
```

The benchmark intentionally consumes the same runtime telemetry exposed to Prometheus.

This keeps the observability model consistent across:

* local benchmarking;
* Grafana;
* future edge-node TUI tooling;
* Kubernetes deployments.

See [observability.md](observability.md) for the runtime metric inventory and Grafana integration.

## Future benchmark increments

Useful future extensions include:

* automated benchmark matrices;
* comparison reports between benchmark JSON files;
* CPU throttling statistics from cgroup v2;
* configurable benchmark payloads;
* model-specific workloads;
* longer soak tests;
* performance regression thresholds in CI;
* memory-policy comparisons;
* ONNX model optimization;
* FP32 versus INT8 model comparisons;
* power and energy measurements where suitable telemetry is available;
* network and connectivity experiments for bandwidth-constrained edge operation.
