# Real-Time AQI Tracking Platform

A full-stack air quality monitoring system that ingests live PM2.5 data from the OpenWeather API, computes US EPA AQI, forecasts the next 24 hours with XGBoost, detects anomalies with IsolationForest, and fires email alerts when thresholds are breached.

---

## Features

| Area | Details |
|------|---------|
| **Ingestion** | Polls OpenWeather Air Pollution API every 10 min for all tracked cities |
| **AQI** | US EPA PM2.5 breakpoint formula; six health categories |
| **Forecasting** | XGBoost recursive 24-h forecast; retrained nightly at 02:00 |
| **Anomaly detection** | IsolationForest (contamination = 5 %) flags per-reading spikes |
| **Alerting** | Threshold rules (global + per-city), 60-min dedup, email via SMTP |
| **Analytics** | Daily/hourly averages, pollutant breakdown, city comparison, data-gap detection |
| **Frontend** | Interactive world map, city dashboard, historical trends, forecast chart, alert table |

---

## Tech Stack

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, asyncpg, APScheduler, XGBoost, scikit-learn, pandas, httpx

**Frontend** — React 18, TypeScript (strict), Vite 8, Tailwind CSS v4, Recharts, Leaflet / react-leaflet, React Router v7, Axios

**Infrastructure** — PostgreSQL 15, Docker Compose (multi-stage builds, named networks, resource limits)

---

## Quick Start

### Prerequisites

- Docker Desktop (with Linux containers)
- OpenWeather API key — free tier at <https://openweathermap.org/api>
- Gmail App Password for email alerts (optional)

### 1. Clone and configure

```bash
git clone <repo-url>
cd Real-Time-AQI-Tracking-Platform
cp .env.example .env
```

Edit `.env`:

```
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

Three containers start:

| Container | Role | Port |
|-----------|------|------|
| `aqi_db` | PostgreSQL 15 | 5434 (host) |
| `aqi_backend` | FastAPI + scheduler | 8000 |
| `aqi_frontend` | Vite dev server | 5173 |

### 3. Seed locations and run migrations

```bash
# Apply database schema
docker exec aqi_backend alembic upgrade head

# Seed tracked cities
docker exec aqi_backend python app/seeds.py
```

### 4. Open the app

| URL | Description |
|-----|-------------|
| <http://localhost:5173> | Frontend |
| <http://localhost:8000/docs> | Interactive API docs (Swagger) |
| <http://localhost:8000/redoc> | ReDoc API reference |

The ingestion scheduler fires within 10 minutes of startup. AQI data and the map populate automatically.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWEATHER_API_KEY` | Yes | — | OpenWeather free-tier key |
| `DATABASE_URL` | Yes | — | Full asyncpg connection string |
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

---

## API Reference

All endpoints are prefixed with `/api`. Interactive docs at `/docs`.

### Locations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/locations` | List all tracked cities |

### AQI

| Method | Path | Query params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/aqi/current` | `city` | Latest reading + category |
| `GET` | `/api/aqi/history` | `city`, `days` (1–90, default 7) | Historical readings |
| `GET` | `/api/aqi/pollutants` | `city` | Latest PM2.5, PM10, CO, NO₂, SO₂, O₃ |
| `GET` | `/api/aqi/forecast` | `city` | Next 24-h XGBoost predictions |

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/alerts` | Active alerts (newest first) |
| `POST` | `/api/alerts/rules` | Create a threshold rule |
| `PATCH` | `/api/alerts/{id}/resolve` | Resolve an alert |

**Default threshold rules** (seeded at startup):

| Type | Threshold |
|------|-----------|
| `unhealthy` | AQI > 150 |
| `very_unhealthy` | AQI > 200 |
| `hazardous` | AQI > 300 |

### Analytics

| Method | Path | Query params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/analytics/city-comparison` | — | Latest AQI for all cities |
| `GET` | `/api/analytics/trends` | `city`, `period` (daily/weekly/monthly) | Daily avg/min/max over period |
| `GET` | `/api/analytics/peak-hours` | `city` | Average AQI by hour of day |
| `GET` | `/api/analytics/distribution` | `city` | Reading count per EPA category |
| `GET` | `/api/analytics/gaps` | `city`, `lookback_hours`, `threshold_minutes` | Data gaps in recent history |

---

## Tracked Cities

Bangkok, Beijing, Cairo, Colombo, Delhi, Jakarta, Karachi, Lagos, Mexico City, Mumbai, Sao Paulo, Seoul, Shanghai, Tokyo, and more — see `backend/app/seeds.py`.

---

## Scheduler Jobs

| Job | Schedule | Action |
|-----|----------|--------|
| Ingest all locations | Every 10 min | Fetch API → validate → save → check alerts |
| Hourly forecast | Every hour | Run XGBoost for each city, replace predictions |
| Retrain models | Daily 02:00 | Re-fit XGBoost + IsolationForest on last 30 days |

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
docker exec aqi_backend pip install pytest pytest-asyncio
docker exec aqi_backend python -m pytest tests/test_api.py -v
```

22 tests covering all API routes via in-process ASGI transport.

### End-to-end smoke test (requires full stack running)

```bash
python scripts/smoke_test.py
```

23 checks: container health, all API endpoints, OpenAPI docs, and the frontend dev server.

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (aqi, alerts, analytics, locations)
│   │   ├── ml/           # XGBoost forecasting + IsolationForest anomaly detection
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic v2 request/response schemas
│   │   ├── services/     # Ingestion, alert engine, analytics queries
│   │   ├── config.py     # pydantic-settings (reads .env)
│   │   └── main.py       # FastAPI app + lifespan
│   ├── alembic/          # Database migrations
│   ├── pipeline/
│   │   └── scheduler.py  # APScheduler jobs
│   └── tests/            # pytest unit + integration tests
├── frontend/
│   └── src/
│       ├── components/   # AQICard, AQIMap, TrendChart, PollutantChart, ForecastChart, AlertBanner, Navbar
│       ├── pages/        # Home, CityDashboard, Historical, Forecast, Alerts
│       ├── services/     # Typed Axios API client
│       └── utils/        # AQI colour + category helpers
├── scripts/
│   └── smoke_test.py     # End-to-end smoke test
├── docker-compose.yml         # Production service definitions
├── docker-compose.override.yml # Dev overrides (hot-reload, port 5434)
└── .env.example
```

---

## Development Notes

**Hot reload** — both backend (uvicorn `--reload`) and frontend (Vite HMR) reflect code changes without container restarts.

**Database migrations** — add a model, generate, and apply:

```bash
docker exec aqi_backend alembic revision --autogenerate -m "describe change"
docker exec aqi_backend alembic upgrade head
```

**Email alerts** — require a Gmail App Password (not your regular password). Generate one at <https://myaccount.google.com/apppasswords> and set `SMTP_PASSWORD` in `.env`. After updating `.env`, recreate the backend container:

```bash
docker-compose up -d --force-recreate backend
```

**ML models** — stored as `.pkl` files under `backend/models/`. The first forecast run is skipped until at least 5 readings exist per city. Models improve as data accumulates.
