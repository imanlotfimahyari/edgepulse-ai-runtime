# Runtime Benchmarking

EdgePulse includes a lightweight benchmark client for measuring inference performance and resource efficiency under constrained edge-runtime budgets.

The benchmark is implemented with the Python standard library so it can run without requiring a separate load-testing framework.

The objective is not only to measure maximum requests per second. The benchmark is designed to show how much useful inference work the runtime can perform for a given CPU and memory budget, how latency changes as concurrency approaches saturation, how ONNX Runtime execution strategies affect constrained workloads, and whether model optimizations produce measurable deployment benefits.

## Benchmark client

The benchmark client is located at:

```text
scripts/benchmark_runtime.py
```

It sends HTTP inference requests to the runtime, samples runtime resource metrics, reads model and execution metadata, and optionally writes the result to a machine-readable JSON file.

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
* active execution-profile metadata;
* active model path;
* active manifest path;
* artifact filename;
* artifact size;
* artifact SHA-256;
* artifact checksum-verification state;
* whether the active model matches the selected manifest.

Latency is reported as p50, p95, p99, and mean values where applicable.

Recording artifact identity in the result is important for model-comparison experiments. An FP32 and INT8 result should remain attributable to the exact artifact that produced it rather than relying only on filenames chosen by the benchmark operator.

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

This distinction became important during the ONNX memory-policy experiment: repeated runs against one process produced a misleading allocator-history effect, while fresh-process comparisons showed no meaningful memory saving.

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

Concurrency 4 and 8 are therefore not intended as recommended EdgePulse operating points. They are diagnostic stress points that reveal the behavior of the runtime after its useful CPU capacity has already been reached.

## Repeatability

Short performance runs can be affected by:

* host scheduling;
* Docker scheduling;
* CPU frequency changes;
* background processes;
* runtime warm-up;
* filesystem activity;
* allocator history;
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

When testing configuration that can affect process-level memory allocation, restart the runtime between repetitions if retained allocator state could influence the result.

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

## Historical rule-based versus ONNX baseline

Early EdgePulse ONNX experiments used an intentionally tiny graph consisting primarily of:

```text
Abs
  |
ReduceMean
```

That artifact was approximately:

```text
270 bytes
```

Those experiments were useful for validating the ONNX Runtime path and comparing basic runtime behavior, but they were not suitable for meaningful quantization because the graph had no learned-style weight initializers.

The model was therefore replaced by a deterministic, weight-bearing FP32 model for the optimization experiments.

Historical rule-based-versus-ONNX benchmark values should not be directly compared with the current FP32/INT8 model results because the inference artifact changed.

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

An early `performance` candidate enabled parallel graph execution. Under the 0.5-core test quota and the lightweight ONNX graph used at the time, that configuration was dramatically slower and was rejected.

A later single-threaded spinning candidate was tested as a potential `latency` profile. Repeated measurements did not show a consistent latency advantage over `eco`, so it was also removed.

The final public profiles therefore represent configurations with defensible, distinct purposes rather than preserving profile names that the benchmark evidence did not support.

## Historical execution-profile observations

The profile matrix was run across concurrency levels 1, 2, 4, and 8 under:

```text
CPU:     0.5 core
Memory:  512 MiB
```

Representative median results included:

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

These results demonstrated an important edge-runtime point:

> More inference threads are not automatically better when the container has significantly less than one CPU core available.

For that workload, `eco` frequently improved throughput and inferences per CPU-second while using a simpler execution model.

`balanced` remains useful as the general-purpose/default ONNX Runtime execution strategy and may become preferable as model complexity or the available CPU budget increases.

The FP32-versus-INT8 experiment described below fixes the execution profile to `eco` to isolate the effect of model representation. It does not constitute a new `eco`-versus-`balanced` comparison for the weight-bearing model.

## Weight-bearing FP32 model

The current FP32 artifact is:

```text
runtime/models/anomaly_score.onnx
```

It is generated deterministically by:

```text
scripts/create_onnx_model.py
```

The graph preserves the original EdgePulse score semantics while introducing actual FP32 weight tensors:

```text
features [N]
    |
   Abs
    |
ReduceMean
    |
 Reshape
    |
 MatMul
    |
   Add
    |
  ReLU
    |
 MatMul
    |
   Add
    |
  ReLU
    |
 MatMul
    |
   Add
    |
anomaly_score
```

The model remains compatible with arbitrary non-empty feature-vector lengths because the variable-length input is reduced to a scalar summary before entering the weighted layers.

Its purpose is not to represent a trained production anomaly detector.

It is an infrastructure-oriented inference artifact designed to make the following experiments meaningful:

* ONNX model packaging;
* model manifests;
* quantization;
* artifact-size comparison;
* runtime performance comparison;
* constrained CPU execution;
* runtime memory behavior.

Current FP32 artifact size:

```text
135,289 bytes
```

## Dynamic INT8 quantization

The INT8 model is generated by:

```text
scripts/quantize_onnx_model.py
```

The quantization pipeline:

1. performs ONNX shape preprocessing;
2. preserves the basic graph structure rather than applying an unrelated optimization pass;
3. dynamically quantizes `MatMul` weights;
4. uses per-channel signed INT8 weights;
5. validates the resulting ONNX model.

The generated artifact is:

```text
runtime/models/anomaly_score_int8.onnx
```

Current INT8 artifact size:

```text
40,175 bytes
```

Artifact-size reduction:

```text
approximately 70.3%
```

The resulting graph contains dynamic quantization operations such as:

```text
DynamicQuantizeLinear
MatMulInteger
Cast
Mul
```

The weights are stored as quantized INT8 tensors with per-channel scales and zero points.

This is **dynamic quantization**, not static calibration-based quantization.

Activations are quantized during inference, which introduces runtime work and explains why INT8 is not guaranteed to be faster at every load level.

## Numerical FP32-versus-INT8 validation

The comparison tool is:

```text
scripts/compare_onnx_models.py
```

The validation sweep used:

```text
samples:       1,501
score range:   0.0 to 1.5
threshold:     0.65
```

Observed results:

```text
mean absolute error:           0.0001169
p95 absolute error:            0.0002221
maximum absolute error:        0.0002338
mean relative error:           0.0001558
classification mismatches:     0
classification mismatch ratio: 0.0
```

Worst observed score comparison:

```text
input: 1.5

FP32:
1.5000001192

INT8:
1.5002338886

absolute error:
0.0002337694
```

The conclusion for this model is:

> Dynamic INT8 quantization introduces very small score drift and did not change threshold-based classification in the tested score sweep.

This is not a general accuracy claim for quantized ML models.

## FP32-versus-INT8 constrained benchmark

The controlled model comparison fixed:

```text
backend:            ONNX
execution profile:  eco
CPU budget:         0.5 core
memory limit:       512 MiB
warm-up:            2 seconds
duration:           20 seconds
repetitions:        3
concurrency:        1, 2, 4, 8
```

Only the model artifact changed between FP32 and INT8 runs.

Median results:

| Variant |  C | Throughput req/s | Client p95 | Inference p95 | CPU budget | Avg memory | Infer/CPU-s |
| ------- | -: | ---------------: | ---------: | ------------: | ---------: | ---------: | ----------: |
| FP32    |  1 |           463.42 |   2.575 ms |      0.163 ms |      88.7% |   64.2 MiB |     1033.33 |
| FP32    |  2 |           471.48 |   4.422 ms |      0.434 ms |      97.4% |   64.1 MiB |      968.17 |
| FP32    |  4 |           488.95 |  48.472 ms |      0.804 ms |      97.4% |   64.8 MiB |     1004.11 |
| FP32    |  8 |           494.80 |  63.506 ms |      1.198 ms |      97.3% |   65.5 MiB |     1017.27 |
| INT8    |  1 |           458.48 |   3.619 ms |      0.265 ms |      90.6% |   59.5 MiB |     1021.75 |
| INT8    |  2 |           484.89 |   4.199 ms |      0.411 ms |      97.3% |   59.3 MiB |      992.01 |
| INT8    |  4 |           505.94 |  48.792 ms |      0.776 ms |      97.2% |   60.0 MiB |     1041.38 |
| INT8    |  8 |           506.13 |  63.664 ms |      1.159 ms |      97.4% |   60.9 MiB |     1039.63 |

Run-to-run throughput spread was:

```text
FP32 c1: 4.7%
FP32 c2: 6.5%
FP32 c4: 5.3%
FP32 c8: 0.6%

INT8 c1: 8.5%
INT8 c2: 2.8%
INT8 c4: 4.2%
INT8 c8: 3.2%
```

## Interpreting the model comparison

At concurrency 2:

```text
throughput:
471.48 -> 484.89 req/s
approximately +2.8%

client p95:
4.422 -> 4.199 ms
approximately -5.0%

inference p95:
0.434 -> 0.411 ms
approximately -5.3%

average memory:
64.1 -> 59.3 MiB
approximately -7.5%

inferences / CPU-second:
968.17 -> 992.01
approximately +2.5%
```

The strongest INT8 benefit is model footprint:

```text
135,289 bytes -> 40,175 bytes
approximately -70.3%
```

At concurrency 1, INT8 produced slightly lower throughput and substantially higher inference latency.

This is consistent with the additional runtime work introduced by dynamic activation quantization.

At concurrency 2, 4, and 8, INT8 produced small throughput and inference-efficiency improvements.

The defensible conclusion is therefore:

> Dynamic INT8 quantization is a strong model-footprint optimization and a modest runtime-efficiency optimization for the current constrained EdgePulse workload. It is not universally faster than FP32.

## Saturation behavior

The FP32 result illustrates why concurrency 4 and 8 are still useful test points.

From concurrency 2 to concurrency 4:

```text
CPU budget:
97.4% -> 97.4%

throughput:
471.48 -> 488.95 req/s

client p95:
4.422 -> 48.472 ms
```

CPU consumption is already effectively at the 0.5-core quota at concurrency 2.

Additional concurrency therefore creates relatively little extra throughput while dramatically increasing request waiting time.

The same basic pattern appears with INT8.

For the current resource envelope:

> Concurrency 2 remains a useful low-latency operating point. Concurrency 4 and 8 are saturation/stress observations rather than recommended steady-state configurations.

## ONNX memory-policy experiment

EdgePulse also evaluated whether changing ONNX Runtime memory behavior could justify a dedicated low-memory runtime profile.

The candidate settings were:

```text
CPU memory arena
memory pattern
```

The initial matrix compared:

```text
default:
arena ON
pattern ON

arena-off:
arena OFF
pattern ON

pattern-off:
arena ON
pattern OFF

compact:
arena OFF
pattern OFF
```

The first repeated-process measurements appeared to show:

```text
default:
~99.8 MiB average

alternative policies:
~58-59 MiB average
```

That apparent saving was large enough to require confirmation.

The experiment was repeated with a stricter methodology:

```text
restart runtime before every repetition
same INT8 artifact
same eco execution profile
same 0.5 CPU limit
same 512 MiB memory limit
same concurrency 2 workload
```

Fresh-process medians were:

| Policy             |   Throughput | Client p95 | Avg memory | Max memory |
| ------------------ | -----------: | ---------: | ---------: | ---------: |
| Default            | 487.66 req/s |   4.488 ms |   59.4 MiB |   72.5 MiB |
| CPU arena disabled | 489.95 req/s |   5.475 ms |   59.2 MiB |   71.8 MiB |

The average-memory difference was approximately:

```text
0.2 MiB
```

which is not operationally meaningful.

Disabling the CPU memory arena also produced worse p95 latency in the confirmation runs.

The conclusion was therefore:

> Keep ONNX Runtime's default memory behavior. Do not expose a `compact` memory profile or additional allocator configuration.

The experiment demonstrates why benchmark process state matters. Allocator history can make repeated measurements against one long-lived process look like a stable configuration effect when it is not.

## Selecting a model and execution profile

Docker Compose, FP32:

```bash
MODEL_BACKEND=onnx \
EXECUTION_PROFILE=eco \
MODEL_PATH=/app/models/anomaly_score.onnx \
MODEL_MANIFEST_PATH=/app/models/model-manifest.json \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build edgepulse-runtime
```

Docker Compose, INT8:

```bash
MODEL_BACKEND=onnx \
EXECUTION_PROFILE=eco \
MODEL_PATH=/app/models/anomaly_score_int8.onnx \
MODEL_MANIFEST_PATH=/app/models/model-manifest-int8.json \
docker compose \
  -f deploy/docker-compose/docker-compose.yaml \
  up -d --build edgepulse-runtime
```

Kubernetes/Helm, FP32:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco \
  --set runtime.env.modelPath=/app/models/anomaly_score.onnx \
  --set runtime.env.modelManifestPath=/app/models/model-manifest.json
```

Kubernetes/Helm, INT8:

```bash
helm upgrade --install edgepulse-runtime charts/edgepulse-runtime \
  --namespace edgepulse \
  --create-namespace \
  --set runtime.env.modelBackend=onnx \
  --set runtime.env.executionProfile=eco \
  --set runtime.env.modelPath=/app/models/anomaly_score_int8.onnx \
  --set runtime.env.modelManifestPath=/app/models/model-manifest-int8.json
```

Verify the effective runtime state:

```bash
curl -s http://localhost:8080/model/info | jq
```

A correctly matched runtime should report:

```text
artifact_sha256_verified: true
active_model_matches_manifest: true
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

The runtime section includes:

```text
service
model_name
model_version
model_backend
model_path
model_manifest_path
execution_profile
artifact_filename
artifact_size_bytes
artifact_sha256
artifact_sha256_verified
active_model_matches_manifest
```

This keeps benchmark results attributable to the exact deployed artifact.

Example comparison dimensions include:

```text
rule-based vs ONNX
eco vs balanced
concurrency 1 vs 2 vs 4 vs 8
different CPU budgets
different memory budgets
FP32 vs INT8
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
* `edgepulse-top`;
* Kubernetes deployments.

See [observability.md](observability.md) for the runtime metric inventory and Grafana integration.

## Experiment design lessons

The model-optimization work produced several broader lessons.

### Smaller does not automatically mean faster

INT8 reduced the model artifact by approximately 70%, but low-concurrency latency was worse because dynamic activation quantization introduces runtime work.

### High concurrency is diagnostic

Concurrency 4 and 8 helped demonstrate CPU saturation. They are useful because they show the tail-latency cost of operating beyond the useful knee.

### Negative results should remove configuration

The proposed low-memory ONNX configuration did not survive stricter testing, so no memory profile was added.

### Process lifetime affects memory experiments

Allocator-retained state can distort comparisons if multiple runs share the same process.

### Model-specific evidence should remain model-specific

The current results describe one deterministic EdgePulse model under one constrained runtime envelope. They should not be generalized to arbitrary ONNX models, hardware, execution providers, or quantization strategies.

## Future benchmark increments

Useful future extensions include:

* automated benchmark matrices;
* comparison reports between benchmark JSON files;
* CPU throttling statistics from cgroup v2;
* configurable benchmark payloads;
* trained domain-model workloads;
* larger ONNX models;
* static calibration-based quantization;
* longer soak tests;
* performance regression thresholds in CI;
* alternative ONNX Runtime execution providers;
* power and energy measurements where suitable telemetry is available;
* network and connectivity experiments for bandwidth-constrained edge operation.
