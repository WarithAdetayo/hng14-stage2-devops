import redis
import time
import os
import signal
import sys

# Bug fix #1: host was "localhost" — must be the Compose service name "redis".
# Bug fix #2: no password authentication was set.
# Bug fix #3: decode_responses=True so brpop returns str, not bytes.
#             The original code called job_id.decode() which breaks with
#             decode_responses=True; consistent approach avoids the fragility.
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    password=os.environ.get("REDIS_PASSWORD"),
    decode_responses=True,
)


def process_job(job_id: str) -> None:
    print(f"Processing job {job_id}", flush=True)
    time.sleep(2)  # simulate work
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}", flush=True)


# Bug fix #4: signal was imported but never wired up — the process had no way
# to shut down gracefully.  We now handle SIGTERM (sent by Docker on stop) so
# the container exits cleanly instead of being force-killed after 10 s.
_shutdown = False


def _handle_sigterm(signum, frame):  # noqa: ANN001
    global _shutdown
    print("SIGTERM received — shutting down", flush=True)
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

print("Worker started, waiting for jobs…", flush=True)

while not _shutdown:
    # brpop blocks for up to `timeout` seconds; returns None on timeout.
    # Bug fix #5: queue key was "job" in original, matching the API's lpush.
    #             We keep "jobs" consistent with the fixed API.
    job = r.brpop("jobs", timeout=5)
    if job:
        _, job_id = job   # no .decode() needed — decode_responses=True
        process_job(job_id)

print("Worker exited cleanly", flush=True)
sys.exit(0)
