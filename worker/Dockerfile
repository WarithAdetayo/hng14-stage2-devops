# ── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:3.12-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY worker.py .

RUN chown -R appuser:appgroup /app

USER appuser

# The worker has no HTTP server, so we verify liveness by pinging Redis.
# If Redis is unreachable the worker can't do its job — treat as unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c \
        "import redis, os; \
         r = redis.Redis( \
             host=os.environ.get('REDIS_HOST','redis'), \
             port=int(os.environ.get('REDIS_PORT','6379')), \
             password=os.environ.get('REDIS_PASSWORD'), \
         ); \
         r.ping()" \
        || exit 1

CMD ["python", "worker.py"]
