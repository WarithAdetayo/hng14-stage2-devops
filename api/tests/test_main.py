"""
Unit tests for the Job Processor API.

Strategy: We use fakeredis as a drop-in replacement for the real Redis client.
It runs entirely in-process (no network, no daemon) and behaves identically to
the real client for every command we use.  This is better than unittest.mock
because we test *actual Redis command semantics* (lpush, hset, hget) rather
than just checking that mock methods were called.

Before importing `main`, we replace the module-level `r` connection object
with a fakeredis instance so that every route handler uses the fake backend.
"""
import fakeredis
import pytest
from fastapi.testclient import TestClient

import main  # noqa: E402 — import after patching below


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """
    Replace the real Redis connection with an in-process fake for every test.
    """
    server = fakeredis.FakeServer()
    fake_r = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr(main, "r", fake_r)
    yield fake_r


@pytest.fixture()
def client():
    return TestClient(main.app)


# ── Test 1 ──────────────────────────────────────────────────────────────────
def test_create_job_returns_job_id(client):
    """POST /jobs must return a UUID job_id and HTTP 200."""
    response = client.post("/jobs")
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    # Must be a valid UUID string (36 chars, 4 hyphens)
    job_id = body["job_id"]
    assert len(job_id) == 36
    assert job_id.count("-") == 4


# ── Test 2 ──────────────────────────────────────────────────────────────────
def test_create_job_enqueues_and_sets_status(client, fake_redis):
    """
    POST /jobs must push the job_id onto the 'jobs' list and set status=queued.
    """
    response = client.post("/jobs")
    job_id = response.json()["job_id"]

    # Verify the job landed in the queue
    queue_items = fake_redis.lrange("jobs", 0, -1)
    assert job_id in queue_items

    # Verify the initial status hash was created
    status = fake_redis.hget(f"job:{job_id}", "status")
    assert status == "queued"


# ── Test 3 ──────────────────────────────────────────────────────────────────
def test_get_job_returns_correct_status(client, fake_redis):
    """GET /jobs/{id} must return the current status from Redis."""
    # Pre-seed a job directly in the fake store
    fake_redis.hset("job:test-id-123", "status", "completed")

    response = client.get("/jobs/test-id-123")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "test-id-123"
    assert body["status"] == "completed"


# ── Test 4 ──────────────────────────────────────────────────────────────────
def test_get_job_not_found(client):
    """GET /jobs/{id} must return an error dict for unknown job IDs."""
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 200   # spec returns 200 with error body
    assert response.json().get("error") == "not found"


# ── Test 5 ──────────────────────────────────────────────────────────────────
def test_health_check_ok(client, fake_redis):
    """GET /health must return 200 and status=ok when Redis is reachable."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}