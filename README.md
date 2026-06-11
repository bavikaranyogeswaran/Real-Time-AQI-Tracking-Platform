# Real-Time AQI Tracking Platform

A full-stack air quality monitoring system that ingests live PM2.5 data from the OpenWeather API every 10 minutes, computes the US EPA AQI, forecasts the next 24 hours with XGBoost, detects per-reading anomalies with IsolationForest, and fires email alerts when thresholds are breached.

---

## Features

| Area | Details |
|------|---------|
| **Ingestion** | Polls OpenWeather Air Pollution API every 10 min for all tracked cities |
| **AQI** | US EPA PM2.5 breakpoint formula; six health categories |
| **Forecasting** | XGBoost recursive 24-h forecast; retrained nightly at 02:00 UTC |
| **Anomaly detection** | IsolationForest (contamination = 5 %) flags per-reading spikes |
| **Alerting** | Configurable threshold rules (global + per-city), 60-min dedup, email via SMTP |
| **Analytics** | Daily/hourly averages, pollutant breakdown, city comparison, data-gap detection |
| **Frontend** | Interactive world map, city dashboard, historical trends, forecast chart, alert table |
| **Observability** | Prometheus metrics, Grafana dashboard, structured JSON logs, per-request correlation IDs |
| **Hardening** | Per-endpoint rate limiting, security headers, nginx proxy, startup config validation |

---

## Tech Stack

**Backend** — Python 3.11, FastAPI 0.115, SQLAlchemy 2 (async/asyncpg), Alembic, APScheduler, XGBoost, scikit-learn, Prophet, pandas, httpx, slowapi, structlog, prometheus-client

**Frontend** — React 19, TypeScript, Vite 8, Tailwind CSS v4, Recharts, Leaflet / react-leaflet, React Router v7, Axios

**Infrastructure** — PostgreSQL 15, nginx (reverse proxy + static serving), Docker Compose (multi-stage builds, named networks, resource limits)

**Monitoring** — Prometheus v2.55 (15-day TSDB retention), Grafana v11.3 (auto-provisioned datasource + dashboard)

---

## Quick Start

### Prerequisites

- Docker Desktop (Linux containers mode)
- OpenWeather API key — free tier at <https://openweathermap.org/api>
- Gmail App Password for email alerts (optional)

### 1. Clone and configure

```bash
git clone <repo-url>
cd Real-Time-AQI-Tracking-Platform
cp .env.example .env
```

Edit `.env` at minimum:

```env
OPENWEATHER_API_KEY=your_key_here

DATABASE_URL=postgresql+asyncpg://aqi_user:aqi_pass@db:5432/aqi_db
POSTGRES_USER=aqi_user
POSTGRES_PASSWORD=aqi_pass
POSTGRES_DB=aqi_db
```

### 2. Start the stack

```bash
docker-compose up -d --build
```

Five containers start. Database migrations run automatically before the API server starts.

| Container | Role | Host port |
|-----------|------|-----------|
| `aqi_db` | PostgreSQL 15 | 5434 (dev) |
| `aqi_backend` | FastAPI + APScheduler | 8000 |
| `aqi_frontend` | Vite dev server (dev) / nginx (prod) | 5173 / 80 |
| `aqi_prometheus` | Metrics collection | 9090 |
| `aqi_grafana` | Dashboards | 3000 |

### 3. Seed tracked cities

```bash
docker exec aqi_backend python app/seeds.py
```

### 4. Open the app

| URL | Description |
|-----|-------------|
| <http://localhost:5173> | Frontend (dev) |
| <http://localhost:8000/docs> | Interactive API docs (Swagger) |
| <http://localhost:8000/redoc> | ReDoc API reference |
| <http://localhost:9090> | Prometheus |
| <http://localhost:3000> | Grafana (admin / admin) |

The ingestion scheduler fires within 10 minutes of startup. AQI data and the map populate automatically.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWEATHER_API_KEY` | Yes* | — | OpenWeather free-tier key (*warns on startup if missing) |
| `DATABASE_URL` | Yes | — | Full asyncpg connection string — app refuses to start without this |
| `POSTGRES_USER` | Yes | `aqi_user` | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password |
| `POSTGRES_DB` | Yes | `aqi_db` | Database name |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP port (STARTTLS) |
| `SMTP_USERNAME` | No | — | SMTP login (Gmail address) |
| `SMTP_PASSWORD` | No | — | Gmail App Password |
| `ALERT_EMAIL_FROM` | No | — | Sender address for alert emails |
| `ALERT_EMAIL_TO` | No | — | Comma-separated recipient(s) |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `LOG_FORMAT` | No | `console` | Set to `json` in production for structured logging |

`DATABASE_URL` is validated at startup — the container exits immediately with a clear error message if it is not set.

---

## API Reference

All endpoints are prefixed with `/api`. Interactive docs at `/docs`.

### Locations

| Method | Path | Rate limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/api/locations` | 60/min | List all tracked cities |
| `POST` | `/api/locations` | 10/min | Register a new city |

### AQI

| Method | Path | Rate limit | Query params | Description |
|--------|------|-----------|-------------|-------------|
| `GET` | `/api/aqi/current` | 60/min | `city` | Latest reading + EPA category |
| `GET` | `/api/aqi/history` | 30/min | `city`, `days` (1–90, default 7) | Historical readings |
| `GET` | `/api/aqi/pollutants` | 30/min | `city` | Latest PM2.5, PM10, CO, NO₂, SO₂, O₃ |
| `GET` | `/api/aqi/forecast` | 30/min | `city` | Next 24-h XGBoost predictions |

### Alerts

| Method | Path | Rate limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/api/alerts` | 60/min | Active alerts (newest first) |
| `POST` | `/api/alerts/rules` | 10/min | Create a threshold rule |
| `PATCH` | `/api/alerts/{id}/resolve` | 20/min | Resolve an alert |

**Default threshold rules** (seeded at startup):

| Type | Threshold |
|------|-----------|
| `unhealthy` | AQI > 150 |
| `very_unhealthy` | AQI > 200 |
| `hazardous` | AQI > 300 |

### Analytics

| Method | Path | Rate limit | Query params | Description |
|--------|------|-----------|-------------|-------------|
| `GET` | `/api/analytics/city-comparison` | 30/min | — | Latest AQI for all cities |
| `GET` | `/api/analytics/trends` | 30/min | `city`, `period` (daily/weekly/monthly) | Daily avg/min/max over period |
| `GET` | `/api/analytics/peak-hours` | 30/min | `city` | Average AQI by hour of day |
| `GET` | `/api/analytics/distribution` | 30/min | `city` | Reading count per EPA category |
| `GET` | `/api/analytics/gaps` | 30/min | `city`, `lookback_hours`, `threshold_minutes` | Data gaps in recent history |

### Health & Observability

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/live` | Liveness probe — 200 if process is alive |
| `GET` | `/ready` | Readiness probe — 503 if database is unreachable |
| `GET` | `/health` | Deep health: DB status + scheduler job count |
| `GET` | `/metrics` | Prometheus metrics endpoint |

All responses include an `X-Request-ID` header for distributed tracing. Pass your own via `X-Request-ID` request header or one is generated automatically.

---

## Monitoring

### Prometheus

Scrapes `/metrics` on the backend every 15 seconds. Access at <http://localhost:9090>.

Key metrics:

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | `method`, `path`, `status_code` |
| `aqi_ingest_total` | Counter | `city`, `status` (`success`/`error`/`skipped`) |
| `aqi_ingest_duration_seconds` | Histogram | — |

### Grafana

Pre-provisioned at <http://localhost:3000> (admin / admin). The **AQI Platform** dashboard includes:

- HTTP request rate (rps)
- HTTP error rate (4xx + 5xx)
- AQI ingest rate by city and status
- Ingest duration p50 / p95

No manual datasource or dashboard setup required — both are provisioned automatically on first start.

---

## Security

The API ships with production-ready defaults:

- **Security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Permissions-Policy`, `Referrer-Policy`, `Cache-Control: no-store`
- **Rate limiting** — per-IP limits on every endpoint via slowapi; respects `X-Forwarded-For` from nginx
- **nginx hardening** — `server_tokens off`, 1 MB body limit, proxy timeouts, gzip compression, 1-year cache for hashed static assets
- **Non-root container** — backend runs as `appuser`
- **Fail-fast config** — container refuses to start if `DATABASE_URL` is missing; optional secrets emit warnings instead

---

## Tracked Cities

Bangkok, Beijing, Cairo, Colombo, Delhi, Jakarta, Karachi, Lagos, Mexico City, Mumbai, Sao Paulo, Seoul, Shanghai, Tokyo — see [`backend/app/seeds.py`](backend/app/seeds.py).

---

## Scheduler Jobs

| Job | Schedule | Action |
|-----|----------|--------|
| `ingest_all_locations` | Every 10 min | Fetch OpenWeather → validate → save → check alert rules |
| `run_hourly_forecast` | Every 1 hour | Run XGBoost for each city, replace stored predictions |
| `retrain_models_daily` | Daily 02:00 UTC | Re-fit XGBoost + IsolationForest on last 30 days |

---

## Running Tests

### Unit tests (no database required)

```bash
cd backend
python -m pytest tests/test_ingestion.py tests/test_features.py -v
```

51 tests covering AQI calculation, EPA category mapping, reading validation, and feature-matrix construction.

### Integration tests (requires running PostgreSQL on port 5434)

```bash
docker exec aqi_backend python -m pytest tests/test_api.py -v
```

22 tests covering all API routes via in-process ASGI transport.

### End-to-end smoke test (requires full stack running)

```bash
python scripts/smoke_test.py
```

23 checks: container health, all API endpoints, OpenAPI docs, and the frontend dev server.

---

## CI

GitHub Actions runs on every push and pull request:

**Backend** — ruff lint, ruff format check, mypy type check, pytest unit tests

**Frontend** — TypeScript type check (`tsc --noEmit`), ESLint, Vite production build

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers: aqi, alerts, analytics, locations
│   │   ├── ml/           # XGBoost forecasting + IsolationForest anomaly detection
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic v2 request/response schemas
│   │   ├── services/     # Ingestion, alert engine, analytics queries
│   │   ├── config.py     # pydantic-settings (reads .env)
│   │   ├── database.py   # Async engine (lazy-init) + session factory
│   │   ├── logging_config.py  # structlog setup (console dev / JSON prod)
│   │   ├── metrics.py    # Prometheus counters and histograms
│   │   ├── rate_limit.py # slowapi limiter with X-Forwarded-For support
│   │   ├── security_headers.py  # Security headers middleware
│   │   └── main.py       # FastAPI app, lifespan, middleware
│   ├── alembic/          # Database migrations
│   ├── entrypoint.sh     # Runs alembic upgrade head then execs uvicorn
│   ├── pipeline/
│   │   └── scheduler.py  # APScheduler job definitions
│   └── tests/            # pytest unit + integration tests
├── frontend/
│   └── src/
│       ├── components/   # AQICard, AQIMap, TrendChart, PollutantChart, ForecastChart, AlertBanner, Navbar
│       ├── pages/        # Home, CityDashboard, Historical, Forecast, Alerts
│       ├── services/     # Typed Axios API client
│       └── utils/        # AQI colour + category helpers
├── monitoring/
│   ├── prometheus.yml    # Scrape config (15-day retention)
│   └── grafana/
│       ├── dashboards/   # aqi.json — pre-built dashboard
│       └── provisioning/ # Auto-configure datasource + dashboard on first start
├── scripts/
│   └── smoke_test.py
├── docker-compose.yml         # Production service definitions
├── docker-compose.override.yml # Dev overrides (hot-reload, port 5434)
└── .env.example
```

---

## Development Notes

**Hot reload** — both backend (uvicorn `--reload`) and frontend (Vite HMR) reflect code changes without container restarts in dev mode (`docker-compose.override.yml`).

**Database migrations** — add a model, generate, and apply:

```bash
docker exec aqi_backend alembic revision --autogenerate -m "describe change"
docker exec aqi_backend alembic upgrade head
```

Migrations run automatically on every container start via [`entrypoint.sh`](backend/entrypoint.sh).

**Email alerts** — require a Gmail App Password (not your account password). Generate one at <https://myaccount.google.com/apppasswords> and set `SMTP_PASSWORD` in `.env`. After updating `.env`:

```bash
docker-compose up -d --force-recreate backend
```

**Structured logging** — set `LOG_FORMAT=json` in `.env` for production. In dev the default console renderer uses colours when attached to a TTY. Every log line emitted from FastAPI middleware includes `request_id` for correlation.

**ML models** — stored as `.pkl` files under `backend/models/`. The first forecast run is skipped until at least 5 readings exist per city. Models improve as data accumulates.
