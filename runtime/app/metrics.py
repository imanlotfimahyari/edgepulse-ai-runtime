from app.resources import ResourceCollector
from prometheus_client import REGISTRY, Counter, Gauge, Histogram

INFERENCE_REQUESTS = Counter(
    "edgepulse_inference_requests_total",
    "Total number of inference requests.",
    ["device_type", "prediction", "model_backend", "ingestion"],
)

INFERENCE_ERRORS = Counter(
    "edgepulse_inference_errors_total",
    "Total number of inference errors.",
    ["device_type", "model_backend", "ingestion"],
)

INFERENCE_LATENCY_BUCKETS = (
    0.00005,
    0.0001,
    0.0002,
    0.0005,
    0.001,
    0.002,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

INFERENCE_LATENCY = Histogram(
    "edgepulse_inference_latency_seconds",
    "Inference latency in seconds.",
    ["device_type", "model_backend", "ingestion"],
    buckets=INFERENCE_LATENCY_BUCKETS,
)

MODEL_INFO = Gauge(
    "edgepulse_model_info",
    "Model metadata exposed as labels.",
    ["model_name", "model_version", "model_backend"],
)

MODEL_RUNTIME_INFO = Gauge(
    "edgepulse_model_runtime_info",
    "Active model artifact and execution policy metadata.",
    [
        "artifact_filename",
        "execution_profile",
        "artifact_sha256_verified",
        "active_model_matches_manifest",
    ],
)

DEVICE_MESSAGES = Counter(
    "edgepulse_device_messages_total",
    "Total number of device messages received.",
    ["device_type", "ingestion"],
)

MQTT_MESSAGES = Counter(
    "edgepulse_mqtt_messages_total",
    "Total number of MQTT messages consumed.",
    ["topic", "device_type"],
)

MQTT_ERRORS = Counter(
    "edgepulse_mqtt_errors_total",
    "Total number of MQTT consumer errors.",
    ["topic"],
)

MQTT_CONNECTED = Gauge(
    "edgepulse_mqtt_connected",
    "Whether the runtime is currently connected to the MQTT broker.",
)

INFERENCE_IN_PROGRESS = Gauge(
    "edgepulse_inference_in_progress",
    "Number of inference requests currently being processed.",
)

MODEL_ARTIFACT_SIZE = Gauge(
    "edgepulse_model_artifact_size_bytes",
    "Size of the configured model artifact on disk.",
)

RESOURCE_COLLECTOR = ResourceCollector()
REGISTRY.register(RESOURCE_COLLECTOR)
