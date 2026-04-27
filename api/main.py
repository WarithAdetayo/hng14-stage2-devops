from fastapi import FastAPI, HTTPException
import redis
import uuid
import os

app = FastAPI(title="Job Processor API")

# Bug fix #1: host was hardcoded as "localhost" — inside Docker, services
# communicate by their Compose service name, not localhost.
# Bug fix #2: no password auth was configured at all.
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    password=os.environ.get("REDIS_PASSWORD"),
    decode_responses=True,   # returns str, not bytes — no .decode() needed
)


@app.get("/health")
def health():
    """Health-check endpoint required by Docker HEALTHCHECK and orchestration."""
    try:
        r.ping()
    except redis.exceptions.ConnectionError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return {"status": "ok"}


@app.post("/jobs")
def create_job():
    job_id = str(uuid.uuid4())
    r.lpush("jobs", job_id)
    r.hset(f"job:{job_id}", "status", "queued")
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    # decode_responses=True means hget already returns str (or None)
    status = r.hget(f"job:{job_id}", "status")
    if not status:
        return {"error": "not found"}
    return {"job_id": job_id, "status": status}
