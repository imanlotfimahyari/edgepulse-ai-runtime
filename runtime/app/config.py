import os


class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "edgepulse-ai-runtime")
    model_name: str = os.getenv("MODEL_NAME", "edgepulse-anomaly-detector")
    model_version: str = os.getenv("MODEL_VERSION", "0.1.0")
    model_backend: str = os.getenv("MODEL_BACKEND", "rule-based")
    anomaly_threshold: float = float(os.getenv("ANOMALY_THRESHOLD", "0.65"))


settings = Settings()
