# HappyRobot Carrier Sales Agent

Inbound carrier sales automation for freight brokerage operations. A FastAPI backend
that integrates with the HappyRobot voice AI platform to handle carrier calls end-to-end:
load lookup, FMCSA carrier verification, rate negotiation logging, and a live operations
dashboard for your team.

---

## Overview

This service acts as the data layer and decision engine behind a HappyRobot AI voice
workflow. When a carrier calls in, the AI queries this API to find matching loads, verify
carrier eligibility against FMCSA records, and log the outcome of every negotiation.
Operations staff monitor activity in real time via a Streamlit dashboard without touching
the call floor.

---

## Architecture

```
                        Inbound Carrier Call
                               |
                               v
                    +-----------------------+
                    |  HappyRobot Platform  |
                    |  (Voice AI Workflow)  |
                    +-----------+-----------+
                                |  REST (X-API-Key)
                                v
                    +-----------------------+
                    |   FastAPI Backend     |
                    |                       |
                    |  /loads               |
                    |  /verify-carrier      |
                    |  /calls/log           |
                    |  /dashboard/metrics   |
                    +-----------+-----------+
                                |
                    +-----------+-----------+
                    |   SQLite Database     |
                    |   (loads, call_logs)  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |  Streamlit Dashboard  |
                    |  (Ops monitoring)     |
                    +-----------------------+
```

---

## Live Demo

| Resource | URL |
|---|---|
| API | https://happyrobot-carrier-sales-agent-production.up.railway.app |
| Interactive API Docs | https://happyrobot-carrier-sales-agent-production.up.railway.app/docs |
| Dashboard | https://happyrobot-carrier-sales-agent-dashboard.streamlit.app/*(deploy separately — see Docker / Railway sections below)* |
| HappyRobot Workflow | https://platform.happyrobot.ai/fdemyriamrahali/workflows/sy9u89medca5/editor/oxzei14r8anz |

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| API framework | FastAPI | Async-native, automatic OpenAPI docs, fast to iterate |
| Database | SQLite + SQLAlchemy | Zero-config persistence; swap connection string for Postgres in production |
| Validation | Pydantic v2 | Strict typing with field-level coercion for HappyRobot's variable payloads |
| FMCSA integration | httpx (async) | Non-blocking carrier verification with graceful mock fallback |
| Dashboard | Streamlit + Plotly | Rapid ops UI without a separate frontend build pipeline |
| Deployment | Railway / Docker | Single-command deploys; Nixpacks auto-detects Python |

---

## Quick Start — Local

**Prerequisites:** Python 3.11+

```bash
# 1. Clone
git clone https://github.com/myriam-sys/happyrobot-carrier-sales-agent.git
cd happyrobot-carrier-sales-agent

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and set API_KEY and (optionally) FMCSA_API_KEY

# 5. Seed the database
python -m api.seed_data

# 6. Start the API
uvicorn api.main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs

# 7. Start the dashboard (separate terminal)
streamlit run dashboard/app.py
# Dashboard: http://localhost:8501
```

---

## Quick Start — Docker

**Prerequisites:** Docker and Docker Compose

```bash
cp .env.example .env
# Set API_KEY (and optionally FMCSA_API_KEY) in .env

docker-compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

The API container seeds the database automatically on startup. The dashboard container
waits for the API healthcheck to pass before starting.

To stop and remove volumes:

```bash
docker-compose down -v
```

---

## Cloud Deployment — Railway

1. Create a new project in [Railway](https://railway.app) and connect this repository.
2. Railway detects `railway.json` and builds with Nixpacks automatically.
3. Set the following environment variables in the Railway dashboard:

| Variable | Value |
|---|---|
| `API_KEY` | Any strong secret string |
| `FMCSA_API_KEY` | Your FMCSA Query Central web key |
| `DATABASE_URL` | `sqlite:///./data/carrier_sales.db` (default) |

4. Deploy. The `startCommand` in `railway.json` seeds the database and starts the server.

> **Note:** Railway's filesystem is ephemeral. The SQLite database resets on each
> redeploy. The seed script is idempotent and re-populates loads and sample call logs
> automatically. For persistent call history across deploys, migrate to Railway Postgres
> and update `DATABASE_URL` accordingly.

---

## API Endpoints

All endpoints except `/health` require an
`X-API-Key` header matching the configured `API_KEY`.

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/health` | Liveness check — returns `{"status": "ok"}` | No |
| GET | `/loads` | List loads; filter by `origin`, `equipment_type`, `available_only` | Yes |
| GET | `/loads/{load_id}` | Fetch a single load by ID | Yes |
| GET | `/verify-carrier/{mc_number}` | FMCSA carrier lookup with eligibility flag | Yes |
| POST | `/calls/log` | Record a completed call with negotiation outcome | Yes |
| GET | `/calls/log` | Retrieve recent call logs (default last 20, max 100) | Yes |
| GET | `/dashboard/metrics` | Aggregated KPIs, outcome/sentiment breakdown, top lanes | Yes |
| GET | `/debug/verify/{mc_number}` | FMCSA test endpoint; accepts `?mock=true` | No |

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_KEY` | Yes | — | Secret key sent in the `X-API-Key` header by HappyRobot |
| `FMCSA_API_KEY` | No | — | FMCSA Query Central web key. Without it, all carrier lookups return a stub response with `is_eligible: false` |
| `DATABASE_URL` | No | `sqlite:///./data/carrier_sales.db` | SQLAlchemy connection string. Change to a Postgres URL for production scale |

---

## Project Structure

```
happyrobot-carrier-sales-agent/
│
├── api/
│   ├── main.py          # FastAPI app, all endpoints, auth dependency
│   ├── models.py        # Pydantic request/response schemas
│   ├── database.py      # SQLAlchemy ORM models and session factory
│   ├── fmcsa.py         # Async FMCSA API client with mock fallback
│   └── seed_data.py     # 15 freight loads + 15 sample call logs
│
├── dashboard/
│   ├── app.py           # Streamlit operations dashboard
│   └── requirements.txt # Dashboard-only dependencies
│
├── data/                # SQLite database (gitignored)
├── Dockerfile           # API container
├── Dockerfile.dashboard # Dashboard container
├── docker-compose.yml   # Orchestrates API + dashboard
├── railway.json         # Railway deployment configuration
├── Procfile             # Fallback start command
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

---

## Known Limitations

**FMCSA API geo-restriction.** The FMCSA Query Central API blocks requests from
non-US IP addresses. Deployments on European cloud infrastructure (including Railway's
EU regions) will receive 403 responses. The client handles this gracefully: on a 403 or
404, it falls back to a deterministic mock response derived from the MC number's last
digit (odd = eligible, even = ineligible). Affected responses include `"is_mock": true`
in the payload. Use Railway's US region or proxy through a US-based endpoint to get live
FMCSA data.

**SQLite is not production-scale.** SQLite handles the throughput of this demo
comfortably, but it does not support concurrent writes from multiple API workers. For
production deployments with more than one Uvicorn worker or a multi-instance setup,
replace `DATABASE_URL` with a Postgres connection string — no other code changes are
required.

**Ephemeral storage on Railway free tier.** Each redeploy resets the filesystem.
Call log history is lost unless you attach a persistent volume or migrate to Postgres.
