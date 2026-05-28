FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system edgepulse \
    && useradd --system --gid edgepulse --home-dir /app --shell /usr/sbin/nologin edgepulse

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=edgepulse:edgepulse app ./app
COPY --chown=edgepulse:edgepulse models ./models

USER edgepulse

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
