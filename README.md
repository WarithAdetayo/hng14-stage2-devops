# Job Processor — Containerised Microservices

A job processing system composed of four services:

| Service | Tech | Role |
|---|---|---|
| `frontend` | Node.js / Express | Submit jobs and track their status |
| `api` | Python / FastAPI | Create jobs, serve status |
| `worker` | Python | Consume the queue, process jobs |
| `redis` | Redis 7 | Shared message queue + job-state store |

---

## Prerequisites

| Tool | Minimum version | Check |
|---|---|---|
| Docker | 24.x | `docker --version` |
| Docker Compose | v2.x (plugin) | `docker compose version` |
| Git | any recent | `git --version` |

No other tools are needed to run the stack locally.

---

## Quickstart — bring the stack up on a clean machine

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. Create your environment file from the example
cp .env.example .env

# 3. Edit .env — at minimum set a strong REDIS_PASSWORD
#    (The default value in .env.example is intentionally weak.)
nano .env   # or: vim .env / code .env

# 4. Build images and start the stack
docker compose up --build -d

# 5. Verify all services are healthy
docker compose ps
```

**What a successful startup looks like:**

```
NAME                 IMAGE              STATUS
stage2-redis-1       redis:7.2-alpine   Up X seconds (healthy)
stage2-api-1         job-api:latest     Up X seconds (healthy)
stage2-worker-1      job-worker:latest  Up X seconds (healthy)
stage2-frontend-1    job-frontend:latest Up X seconds (healthy)
```

All four containers must show `(healthy)` before the application is ready.
If a container shows `(health: starting)`, wait 30 seconds and re-run `docker compose ps`.

The frontend is accessible at: **http://localhost:3000**

---

## Using the application

1. Open http://localhost:3000 in your browser.
2. Click **Submit New Job** — a job ID appears and polling starts automatically.
3. Within a few seconds the job status changes from `queued` → `completed`.

You can also interact directly with the API:

```bash
# Create a job
curl -X POST http://localhost:8000/jobs

# Check job status (replace <job_id> with the UUID returned above)
curl http://localhost:8000/jobs/<job_id>

# Health check
curl http://localhost:8000/health
```

---

## Environment variables

All configuration is injected via `.env`.  See `.env.example` for the full list.

| Variable | Required | Description |
|---|---|---|
| `REDIS_PASSWORD` | Yes | Password for the Redis instance |
| `FRONTEND_PORT` | No | Host port for the frontend (default: `3000`) |
| `REGISTRY` | Deploy only | Image registry prefix for rolling updates |

---

## Stopping and cleaning up

```bash
# Stop all containers (keep volumes)
docker compose down

# Stop and remove volumes (wipes all job data)
docker compose down -v
```

---

## CI/CD Pipeline

The GitHub Actions pipeline runs on every push and PR, in strict order:

```
lint → test → build → security-scan → integration-test → deploy (main only)
```

| Stage | What it does |
|---|---|
| **lint** | flake8 (Python), eslint (JavaScript), hadolint (Dockerfiles) |
| **test** | pytest with ≥ 5 unit tests; coverage report uploaded as artifact |
| **build** | Builds all 3 images, tags with `<sha>` and `latest`, pushes to a local registry service container; saves tars as artifacts |
| **security-scan** | Trivy scans all images; fails on CRITICAL findings with fixes available; uploads SARIF to GitHub Code Scanning |
| **integration-test** | Brings the full stack up in the runner, submits a job, polls until `completed`, tears down |
| **deploy** | Rolling update via SSH — new container must pass health check before old one stops (60 s timeout) |

### Deploy secrets

Set these in **Settings → Secrets and variables → Actions** in your fork:

| Secret | Description |
|---|---|
| `DEPLOY_HOST` | Hostname / IP of your production server |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | Private key (PEM format) |
| `REGISTRY` | Image registry prefix |

If `DEPLOY_HOST` is not set, the deploy job logs a notice and exits cleanly (all earlier stages still run and pass).

---

## Project layout

```
.
├── api/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Pinned production deps
│   ├── requirements-dev.txt    # Test deps (pytest, fakeredis, httpx)
│   ├── tests/
│   │   └── test_main.py        # 5 unit tests (Redis mocked with fakeredis)
│   └── Dockerfile              # Multi-stage, non-root, HEALTHCHECK
├── worker/
│   ├── worker.py               # Job consumer
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.js                  # Express server
│   ├── package.json
│   ├── .eslintrc.json
│   ├── views/index.html
│   └── Dockerfile
├── scripts/
│   └── rolling-update.sh       # Zero-downtime deploy script
├── .github/
│   └── workflows/
│       └── pipeline.yml        # Full CI/CD pipeline
├── docker-compose.yml
├── .env.example
├── .gitignore
├── FIXES.md                    # All 15 bugs documented
└── README.md
```
