from prometheus_client import Counter, Gauge, Histogram


INFERENCE_REQUESTS = Counter(
    "edgepulse_inference_requests_total",
    "Total number of inference requests.",
    ["device_type", "prediction", "model_backend"],
)

INFERENCE_ERRORS = Counter(
    "edgepulse_inference_errors_total",
    "Total number of inference errors.",
    ["device_type", "model_backend"],
)

INFERENCE_LATENCY = Histogram(
    "edgepulse_inference_latency_seconds",
    "Inference latency in seconds.",
    ["device_type", "model_backend"],
)

MODEL_INFO = Gauge(
    "edgepulse_model_info",
    "Model metadata exposed as labels.",
    ["model_name", "model_version", "model_backend"],
)

DEVICE_MESSAGES = Counter(
    "edgepulse_device_messages_total",
    "Total number of device messages received.",
    ["device_type"],
)
