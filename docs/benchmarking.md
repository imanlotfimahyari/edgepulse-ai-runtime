# Runtime Benchmarking

EdgePulse includes a lightweight benchmark client for measuring inference performance and resource efficiency under constrained edge-runtime budgets.

The benchmark is implemented with the Python standard library so it can run without requiring a separate load-testing framework.

The objective is not only to measure maximum requests per second. The benchmark is designed to show how much useful inference work the runtime can perform for a given CPU and memory budget, and how latency changes as concurrency approaches saturation.

## Benchmark client

The benchmark client is located at:

```text
scripts/benchmark_runtime.py
```

It sends HTTP inference requests to the runtime, samples runtime resource metrics, and optionally writes the result to a machine-readable JSON file.

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
* successful inferences per CPU-second.

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

This metric becomes particularly useful when comparing:

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

The main options are:

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

The validation used for the initial EdgePulse benchmark matrix used:

```text
duration:     20 seconds
warm-up:      2 seconds
repetitions:  3 or more
concurrency:  1, 2, 4, 8
CPU budget:   0.5 core
memory limit: 512 MiB
```

Median values across repeated runs are more useful than treating one short benchmark as an absolute result.

## Initial constrained-runtime experiment

The initial benchmark experiment compared the current rule-based and ONNX backends using the same Compose resource budget:

```text
CPU:     0.5 core
Memory:  512 MiB
```

Repeated measurements showed a consistent saturation pattern.

At concurrency 2, both backends were already using approximately the available 0.5-core CPU budget while maintaining relatively low client p95 latency.

Increasing concurrency to 4 and 8 provided only limited additional throughput while client p95 latency increased substantially.

The practical conclusion for this workload is:

> Under the 0.5-core test budget, concurrency 2 is a useful low-latency operating point. Higher concurrency can extract some additional throughput, but at a disproportionate tail-latency cost.

The experiment also showed that memory was not the limiting resource for the current workload. Runtime memory consumption remained well below the 512 MiB container limit.

## Rule-based versus ONNX

The ONNX backend requires more inference work than the simple rule-based backend.

The repeated measurements showed that, under the same constrained runtime budget:

* ONNX produced lower throughput than the rule-based backend at comparable concurrency;
* ONNX consumed slightly more memory;
* ONNX inference latency was higher;
* ONNX completed fewer inferences per CPU-second;
* both backends became CPU constrained before memory constrained.

These results apply only to the current EdgePulse demo workload.

The packaged ONNX artifact is intentionally tiny and exists to exercise the ONNX Runtime execution path:

```text
models/anomaly_score.onnx
```

Its artifact size is approximately:

```text
270 bytes
```

The benchmark results must therefore not be interpreted as general ONNX Runtime performance characteristics or as representative of production ML models.

Future experiments with larger and more realistic models are expected to produce materially different CPU, memory, and latency behavior.

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

This format allows later scripts or CI jobs to compare benchmark runs programmatically.

Example comparison dimensions include:

```text
rule-based vs ONNX
concurrency 1 vs 2 vs 4 vs 8
different CPU budgets
different memory budgets
eco vs balanced vs performance profiles
FP32 vs quantized models
different ONNX Runtime configurations
```

Benchmark result files produced during ad-hoc validation should normally remain outside the repository unless a particular result is intentionally being preserved as a documented reference experiment.

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
* comparison of runtime execution profiles;
* ONNX Runtime tuning;
* FP32 versus INT8 model comparisons;
* power and energy measurements where suitable telemetry is available.
