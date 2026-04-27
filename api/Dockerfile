# ── Stage 1: dependency builder ─────────────────────────────────────────────
# We install packages here so the final image contains no pip, no compilers,
# and no build-layer cache that could inflate image size.
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

# Install into /install so we can COPY the tree into the final image cleanly.
# --no-cache-dir prevents pip from writing its HTTP cache into the layer.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:3.12-slim

# Create a non-root user before doing anything else — principle of least privilege.
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Bring in only the installed packages from the builder stage.
COPY --from=builder /install /usr/local

COPY main.py .

# Correct ownership so the non-root user can write temp files if needed.
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Health check hits our dedicated /health endpoint.
# start-period gives the app time to boot before the first check.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
        || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
