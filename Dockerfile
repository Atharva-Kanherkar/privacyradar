FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY db /app/db
COPY worker /app/worker

WORKDIR /app/worker
ENV PRIVACYRADAR_MIGRATIONS_DIR=/app/db/migrations \
    CATALOG_PATH=/app/worker/data/catalog.yaml
RUN pip install --no-cache-dir .

CMD ["sh", "-c", "privacyradar migrate && privacyradar seed && exec arq privacyradar.jobs.WorkerSettings"]
