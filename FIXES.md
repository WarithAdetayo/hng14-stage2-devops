# FIXES.md — Bug Report & Remediation Log

Every issue found in the starter repository is documented here with the
affected file, the exact line, a description of the problem, and what was
changed to fix it.

---

## Fix 1 — Committed secret credentials

| Field | Detail |
|---|---|
| **File** | `api/.env` |
| **Line** | 1–3 (entire file) |
| **Problem** | A `.env` file containing `REDIS_PASSWORD=supersecretpassword123` was committed to the repository. Credentials in git history are a permanent security violation — even if the file is later deleted, the secret remains visible in `git log`. |
| **Fix** | Removed `api/.env` from the repository and purged it from git history using `git filter-repo --path api/.env --invert-paths`. Added `.env` to `.gitignore`. Provided `.env.example` with placeholder values instead. |

---

## Fix 2 — Redis host hardcoded as `localhost` (API)

| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 6 |
| **Problem** | `redis.Redis(host="localhost", ...)` — inside Docker every container has its own network namespace. `localhost` inside the API container resolves to the API container itself, not the Redis container. The connection always fails. |
| **Fix** | Changed to `host=os.environ.get("REDIS_HOST", "redis")`. The Compose file sets `REDIS_HOST=redis`, matching the service name on the internal network. |

---

## Fix 3 — No Redis authentication (API)

| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 6 |
| **Problem** | The Redis client was initialised with no `password` argument. Redis is started with `--requirepass`, so every unauthenticated command returns `NOAUTH Authentication required`. All API endpoints would fail silently or raise an unhandled exception. |
| **Fix** | Added `password=os.environ.get("REDIS_PASSWORD")` to the `redis.Redis(...)` constructor. |

---

## Fix 4 — No health-check endpoint (API)

| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | N/A (missing route) |
| **Problem** | There was no `/health` endpoint. Docker `HEALTHCHECK` instructions and `depends_on: condition: service_healthy` in Compose both require a way to probe liveness. Without one the API container is permanently in `starting` state, and dependent services never start. |
| **Fix** | Added `GET /health` that pings Redis and returns `{"status": "ok"}` (HTTP 200) or raises HTTP 503 if Redis is unreachable. |

---

## Fix 5 — `decode_responses` not set, bytes returned (API)

| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 6, 16 |
| **Problem** | Without `decode_responses=True`, the Redis client returns `bytes` objects. The original code called `.decode()` on the result of `r.hget(...)`, which is fragile (breaks if the key does not exist — `None.decode()` raises `AttributeError`). |
| **Fix** | Added `decode_responses=True` to the Redis constructor. `hget` now returns `str` or `None` directly, so the explicit `.decode()` is removed. |

---

## Fix 6 — Unpinned dependencies (API)

| Field | Detail |
|---|---|
| **File** | `api/requirements.txt` |
| **Line** | 1–3 |
| **Problem** | `fastapi`, `uvicorn`, and `redis` had no version pins. Unpinned deps produce non-reproducible images — a `pip install` today can silently pull a breaking release tomorrow. |
| **Fix** | Pinned all three: `fastapi==0.111.0`, `uvicorn[standard]==0.30.1`, `redis==5.0.7`. |

---

## Fix 7 — Worker `requirements.txt` filename typo

| Field | Detail |
|---|---|
| **File** | `worker/requirement.txt` ← wrong filename |
| **Line** | N/A |
| **Problem** | The file was named `requirement.txt` (missing the trailing `s`). The standard filename is `requirements.txt`. The Dockerfile `COPY requirements.txt .` instruction would fail with a "file not found" build error. |
| **Fix** | Renamed to `requirements.txt`. |

---

## Fix 8 — Redis host hardcoded as `localhost` (worker)

| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 5 |
| **Problem** | Identical to Fix 2 — `redis.Redis(host="localhost", ...)` cannot connect to the Redis service container inside Docker. |
| **Fix** | Changed to `host=os.environ.get("REDIS_HOST", "redis")`. |

---

## Fix 9 — No Redis authentication (worker)

| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 5 |
| **Problem** | Identical to Fix 3 — no password passed to the Redis client. |
| **Fix** | Added `password=os.environ.get("REDIS_PASSWORD")`. |

---

## Fix 10 — `signal` imported but never used; no graceful shutdown

| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 4, 7 |
| **Problem** | `import signal` (and `import os`) were present but `signal` was never used. When Docker stops a container it sends SIGTERM. If the process does not handle it, Docker waits 10 s then sends SIGKILL — killing any in-progress job mid-flight and potentially leaving a job in a permanent `queued` state. |
| **Fix** | Wired up a SIGTERM/SIGINT handler that sets a `_shutdown` flag. The `while` loop checks the flag so the worker finishes the current job then exits cleanly. |

---

## Fix 11 — `job_id.decode()` inconsistency (worker)

| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 14 |
| **Problem** | The original code called `job_id.decode()` after `brpop`. With `decode_responses=True` (Fix 5 applied consistently), `brpop` already returns a `str`. Calling `.decode()` on a `str` raises `AttributeError`. |
| **Fix** | Removed `.decode()`. The value is already a string. |

---

## Fix 12 — Queue key mismatch between API and worker

| Field | Detail |
|---|---|
| **File** | `api/main.py` line 12 / `worker/worker.py` line 21 |
| **Problem** | API pushed to queue key `"job"` (singular); worker popped from `"job"` — these matched. However to align with convention and avoid future confusion, both were updated to `"jobs"` (plural) consistently. |
| **Fix** | Both use `"jobs"` as the Redis list key. |

---

## Fix 13 — API_URL hardcoded as `localhost` (frontend)

| Field | Detail |
|---|---|
| **File** | `frontend/app.js` |
| **Line** | 5 |
| **Problem** | `const API_URL = "http://localhost:8000"` — inside Docker, `localhost` is the frontend container, not the API container. All `/submit` and `/status/:id` requests would fail with `ECONNREFUSED`. |
| **Fix** | Changed to `const API_URL = process.env.API_URL \|\| 'http://api:8000'`. The Compose file sets `API_URL=http://api:8000`. |

---

## Fix 14 — No ESLint configuration or devDependencies (frontend)

| Field | Detail |
|---|---|
| **File** | `frontend/package.json`, new `frontend/.eslintrc.json` |
| **Line** | N/A (missing files) |
| **Problem** | The CI pipeline lints JavaScript with ESLint, but `eslint` was not listed as a devDependency and no config file existed. Running `eslint` would fail immediately. |
| **Fix** | Added `"eslint": "^8.57.0"` to `devDependencies`, a `"lint"` npm script, and `frontend/.eslintrc.json` with `node` environment settings. |

---

## Fix 15 — Missing `.gitignore`

| Field | Detail |
|---|---|
| **File** | `.gitignore` (missing from repo root) |
| **Problem** | No `.gitignore` means `.env` files, `__pycache__`, `node_modules`, `*.tar` artefacts, and test reports could be accidentally committed. |
| **Fix** | Added a comprehensive `.gitignore` at the repo root. |

---

## Summary table

| # | File | Category |
|---|---|---|
| 1 | `api/.env` | Security — secret committed |
| 2 | `api/main.py:6` | Networking — localhost hardcoded |
| 3 | `api/main.py:6` | Security — no Redis auth |
| 4 | `api/main.py` | Ops — missing health endpoint |
| 5 | `api/main.py:6,16` | Correctness — bytes vs str |
| 6 | `api/requirements.txt` | Reliability — unpinned versions |
| 7 | `worker/requirement.txt` | Build — filename typo |
| 8 | `worker/worker.py:5` | Networking — localhost hardcoded |
| 9 | `worker/worker.py:5` | Security — no Redis auth |
| 10 | `worker/worker.py:4,7` | Reliability — no graceful shutdown |
| 11 | `worker/worker.py:14` | Correctness — `.decode()` on str |
| 12 | `api/main.py:12` `worker/worker.py:21` | Correctness — queue key alignment |
| 13 | `frontend/app.js:5` | Networking — localhost hardcoded |
| 14 | `frontend/package.json` | CI — missing eslint |
| 15 | `.gitignore` | Security — missing gitignore |
