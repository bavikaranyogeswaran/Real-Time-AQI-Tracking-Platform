# Real-Time AQI Tracking Platform

A production-grade, full-stack air quality monitoring system that ingests live pollutant data from the OpenWeather API every 10 minutes, computes the US EPA AQI, forecasts the next 24 hours with XGBoost, detects per-reading anomalies with IsolationForest, and fires email alerts when thresholds are breached — all running in Docker with Prometheus metrics and Grafana dashboards.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Data Pipeline & Flow](#data-pipeline--flow)
5. [Tech Stack](#tech-stack)
6. [Machine Learning](#machine-learning)
7. [API Reference](#api-reference)
8. [Security](#security)
9. [Monitoring & Observability](#monitoring--observability)
10. [Database Schema](#database-schema)
11. [Quick Start](#quick-start)
12. [Environment Variables](#environment-variables)
13. [Tracked Cities](#tracked-cities)
14. [Scheduler Jobs](#scheduler-jobs)
15. [Running Tests](#running-tests)
16. [CI/CD](#cicd)
17. [Project Structure](#project-structure)
18. [Development Notes](#development-notes)

---

## Overview

Air quality is a critical public health metric affecting billions of people worldwide. This platform provides a unified, real-time view of Air Quality Index (AQI) data across 12 major global cities — from Colombo to Beijing, Delhi to New York — enabling users to monitor current conditions, review historical trends, anticipate future pollution levels, and receive automated alerts when air quality deteriorates.

The platform is built around three core principles:

**Reliability** — Data is validated before storage, deduplicated at the database level, and anomalous spikes are flagged automatically. Health probes and readiness checks ensure the system self-reports problems instantly.

**Observability** — Every HTTP request carries a correlation ID. Ingestion metrics, error rates, and latency histograms are scraped by Prometheus and visualised in a pre-built Grafana dashboard. Structured JSON logs (in production) enable log aggregation at scale.

**Security** — Rate limits are enforced per endpoint and per IP. Security headers (HSTS, CSP directives, `X-Frame-Options`) are injected on every response. The backend process runs as a non-root container user. The application refuses to start if mandatory secrets are absent.

---

## Features

| Area | Details |
|------|---------|
| **Real-time ingestion** | Polls OpenWeather Air Pollution API every 10 minutes for all tracked cities; validates, deduplicates, and persists readings |
| **EPA AQI calculation** | US EPA PM2.5 breakpoint formula across all six health categories (Good → Hazardous); 3-sigma outlier detection on ingestion |
| **24-hour forecasting** | XGBoost recursive model using lag features (1 h, 3 h, 24 h), temporal features (hour, weekday, month), and all six pollutants; retrained nightly |
| **Anomaly detection** | IsolationForest (contamination = 5 %) scores every reading and creates `anomaly_spike` alerts for statistical outliers |
| **Threshold alerting** | Configurable global + per-city rules; 60-minute deduplication window prevents alert spam; email delivery via SMTP |
| **Historical analytics** | Daily/hourly averages, pollutant breakdown, city-to-city comparison, peak-hour profiling, data-gap detection |
| **Interactive frontend** | World map (Leaflet), city dashboard, trend charts, 24-hour forecast chart, and live alert table built in React 19 + TypeScript |
| **Observability** | Prometheus metrics endpoint, auto-provisioned Grafana dashboard, structured logs, per-request `X-Request-ID` |
| **Hardening** | Per-endpoint rate limiting (slowapi), OWASP security headers, nginx reverse proxy, non-root container, fail-fast config validation |
| **Developer experience** | Hot-reload in dev (uvicorn `--reload` + Vite HMR), pre-commit hooks (ruff + ESLint), type-checked (mypy + tsc), GitHub Actions CI |

---

## System Architecture

The platform is composed of five containerised services, all orchestrated with Docker Compose:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Network                              │
│                                                                     │
│  ┌──────────────┐    proxy /api    ┌──────────────────────────────┐ │
│  │   Frontend   │ ───────────────► │         Backend              │ │
│  │  React + TS  │                  │  FastAPI  +  APScheduler     │ │
│  │  nginx:80    │                  │  uvicorn : 8000              │ │
│  └──────────────┘                  └────────────┬─────────────────┘ │
│                                                 │                   │
│                            ┌────────────────────┼──────────────┐   │
│                            ▼                    ▼              ▼   │
│                   ┌──────────────┐   ┌──────────────┐  ┌──────────┐│
│                   │  PostgreSQL  │   │  Prometheus  │  │ Grafana  ││
│                   │     :5432    │   │    :9090     │  │  :3000   ││
│                   └──────────────┘   └──────────────┘  └──────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

External dependency:
  APScheduler (inside backend) → OpenWeather API (https)
  Alert engine (inside backend) → Gmail SMTP (TLS :587)
```

**Frontend** serves the production Vite bundle via nginx, which also reverse-proxies `/api/*` requests to the backend. This single-origin design eliminates CORS complexity in production and lets nginx handle gzip compression and long-lived caching of hashed static assets.

**Backend** is a FastAPI application with two embedded subsystems: the HTTP API (served by uvicorn) and the background scheduler (APScheduler). Both share the same SQLAlchemy async session factory and PostgreSQL connection pool, which avoids a separate worker process while keeping memory overhead low.

**PostgreSQL** is the single source of truth. All time-series data is stored in one normalised schema. A composite unique index on `(location_id, timestamp)` enforces deduplication at the database level, providing a safety net on top of the application-layer check.

**Prometheus** scrapes `/metrics` every 15 seconds. Grafana reads from Prometheus and renders the pre-built dashboard automatically on first start — no manual setup required.

---

## Data Pipeline & Flow

### Ingestion (every 10 minutes)

```
APScheduler trigger
      │
      ▼
 For each tracked city:
      │
      ├── 1. HTTP GET  openweathermap.org/data/2.5/air_pollution?lat=…&lon=…
      │         Response: { list[0].components: { pm2_5, pm10, co, no2, so2, o3 } }
      │
      ├── 2. Validation
      │         • All six pollutant fields present
      │         • PM2.5 in [0, 500.4] µg/m³
      │         • No negative concentrations
      │         → Invalid readings increment aqi_ingest_total{status=error} and are dropped
      │
      ├── 3. AQI Calculation  (US EPA PM2.5 breakpoints, linear interpolation)
      │         PM2.5 µg/m³  →  AQI 0–500+  →  EPA category (Good / Moderate / … / Hazardous)
      │
      ├── 4. Outlier pre-screen  (3-sigma z-score over last 10 readings per city)
      │         Spikes are flagged in the log but still stored
      │
      ├── 5. Deduplication check  (SELECT WHERE location_id = … AND timestamp = …)
      │         Duplicate → increment aqi_ingest_total{status=skipped} and skip
      │
      ├── 6. Persist  AirQualityReading row
      │
      ├── 7. Alert rule evaluation
      │         For each active AlertRule (global + city-specific):
      │           If aqi > threshold AND no open alert within last 60 min:
      │             → INSERT Alert row
      │             → Send email via SMTP (async, non-blocking)
      │
      └── 8. Anomaly detection  (IsolationForest — if model trained)
                If isolation score < 0 → INSERT Alert{type="anomaly_spike"}
```

### Forecasting (every hour)

```
APScheduler trigger
      │
      ▼
 For each city with ≥5 readings:
      │
      ├── 1. Load last 7 days of AirQualityReading rows
      │
      ├── 2. Feature engineering
      │         • Lag features: AQI at t-1h, t-3h, t-24h
      │         • Pollutant values: PM2.5, PM10, CO, NO₂, SO₂, O₃
      │         • Temporal: hour-of-day, day-of-week, month, is_weekend flag
      │
      ├── 3. Load (or train) XGBoost model from disk  ({city}_forecast.pkl)
      │
      ├── 4. Recursive 24-step prediction
      │         Each predicted AQI feeds back as the lag feature for the next step
      │
      ├── 5. DELETE existing predictions for this city  (replace, not append)
      │
      └── 6. INSERT 24 × AQIPrediction rows (one per hour ahead)
```

### Nightly retraining (02:00 UTC)

```
APScheduler cron trigger
      │
      ▼
 For each city:
      ├── Load last 30 days of readings
      ├── Re-fit XGBRegressor  (n_estimators=200, max_depth=6, lr=0.05)
      ├── Re-fit IsolationForest  (contamination=0.05, n_jobs=-1)
      └── Serialize both models to  backend/models/{city}_{model}.pkl
```

---

## Tech Stack

**Backend** — Python 3.11, FastAPI 0.115, SQLAlchemy 2 (async/asyncpg), Alembic, APScheduler, XGBoost 2.1, scikit-learn, Prophet 1.1, pandas, httpx, slowapi, structlog, prometheus-client

**Frontend** — React 19, TypeScript, Vite 8, Tailwind CSS v4, Recharts, Leaflet / react-leaflet, React Router v7, Axios

**Infrastructure** — PostgreSQL 15, nginx (reverse proxy + static serving), Docker Compose (multi-stage builds, named networks, resource limits)

**Monitoring** — Prometheus v2.55 (15-day TSDB retention), Grafana v11.3 (auto-provisioned datasource + dashboard)

---

### Backend

| Component | Library / Version |
|-----------|-------------------|
| Language | Python 3.11 |
| Web framework | FastAPI 0.115 |
| ASGI server | uvicorn (standard) |
| ORM | SQLAlchemy 2 (async + asyncpg) |
| Migrations | Alembic 1.14 |
| Scheduler | APScheduler 3.10 |
| HTTP client | httpx 0.27 |
| Forecasting | XGBoost 2.1 |
| Anomaly detection | scikit-learn (IsolationForest) |
| Time-series (optional) | Prophet 1.1 |
| Data processing | pandas 2.2, numpy 1.26 |
| Metrics | prometheus-client 0.21 |
| Logging | structlog 25.4 |
| Rate limiting | slowapi 0.1 |
| Config | pydantic-settings 2.6 |
| Linting / format | ruff 0.11 |
| Type checking | mypy |
| Testing | pytest |

### Frontend

| Component | Library / Version |
|-----------|-------------------|
| Language | TypeScript 6.0 |
| Framework | React 19 |
| Build tool | Vite 8 |
| Styling | Tailwind CSS v4 |
| Charts | Recharts 3.8 |
| Maps | Leaflet 1.9 + react-leaflet 5.0 |
| Routing | React Router v7 |
| HTTP client | Axios 1.17 |
| Linting | ESLint 10 |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 15 (Alpine) |
| Reverse proxy | nginx (Alpine) |
| Containerisation | Docker multi-stage builds |
| Orchestration | Docker Compose v3 |
| Metrics | Prometheus v2.55 (15-day retention) |
| Dashboards | Grafana v11.3 (auto-provisioned) |
| CI | GitHub Actions |

---

## Machine Learning

### XGBoost Forecasting

#### Why XGBoost

The forecasting approach converts the raw time-series into a **tabular regression problem** by engineering lag features, pollutant values, and temporal features. Once the data is in that form, XGBoost — a gradient-boosted decision tree ensemble — is in its natural habitat: fixed-width rows of mixed numerical features with a continuous target.

**Comparison with common alternatives:**

| Algorithm | Why it was passed over |
|-----------|------------------------|
| **ARIMA / SARIMA** | Univariate only — cannot ingest PM2.5, PM10, CO, NO₂, SO₂, O₃ as simultaneous inputs. Assumes linear structure and stationarity, which AQI data rarely satisfies. |
| **Prophet** | Built for business trend + seasonality decomposition (holidays, changepoints). Does not accept the multi-pollutant feature vector this model uses. Included as a dependency for potential future trend analysis. |
| **LSTM / GRU** | Requires substantially more data to generalise — cities start with as few as 5 readings. Also requires normalisation, GPU-friendly hardware, and much longer training loops. Too heavy for nightly CPU retraining on per-city pkl files. |
| **Linear Regression** | Captures linear patterns only. Pollution has pronounced non-linear diurnal cycles (rush hour, temperature inversion, industrial patterns) that a linear model systematically misses. |
| **Random Forest** | Structurally similar but XGBoost consistently outperforms it on tabular data because boosting corrects residual errors sequentially rather than averaging independent trees. |
| **LightGBM** | Nearly equivalent. XGBoost was chosen for its broader ecosystem support and simpler serialisation. Dataset sizes here (≤ 4,320 rows per city at 30-day max) are too small for LightGBM's histogram-based speed advantage to matter. |

**Properties that match this project's constraints:**

- **Small per-city datasets** — With 10-minute ingestion over 30 days the training set is ~4,320 rows per city. XGBoost converges reliably at this scale; neural approaches would overfit.
- **No preprocessing required** — Handles mixed feature scales natively. No normalisation or standardisation step is needed, eliminating a class of training/inference mismatch bugs.
- **Native missing value handling** — If a pollutant reading is absent, XGBoost routes the sample through its learned default direction. The code fills missing values with `0.0` as a fallback, but the model degrades gracefully either way.
- **Recursive forecasting compatibility** — The 24-step recursive strategy feeds each predicted AQI back as the lag feature for the next step. This works with any point estimator that produces a scalar output, so XGBoost slots in without modification.
- **Fast nightly retraining** — Training on ~4,320 rows takes seconds on CPU, making the 02:00 UTC retraining job trivially fast. The model serialises to a small `.pkl` file.
- **Interpretable feature importances** — If a forecast degrades unexpectedly, XGBoost's built-in importances make it straightforward to identify which lag or pollutant drove the prediction.

#### Model details

The forecasting model uses a recursive, single-step prediction strategy: the model is trained to predict AQI one step (one hour) ahead, and at inference time its own output feeds back as the lag feature for subsequent steps. This allows an arbitrary-length forecast horizon from a single trained model.

**Features** (19 total):
- Pollutant values at the current timestep: PM2.5, PM10, CO, NO₂, SO₂, O₃
- AQI lag features: t-1h, t-3h, t-24h
- Temporal features: hour-of-day (0–23), day-of-week (0–6), month (1–12), is_weekend (0/1)

**Hyperparameters**: `n_estimators=200`, `max_depth=6`, `learning_rate=0.05`

**Training data**: Last 30 days of readings per city (retrained nightly at 02:00 UTC)

**Minimum data requirement**: Cities with fewer than 5 readings are skipped — forecasts populate as data accumulates

**Storage**: Models are serialised as `{location_id}_forecast.pkl` under `backend/models/` and hot-loaded at forecast time without restart

### IsolationForest Anomaly Detection

IsolationForest is an unsupervised tree-based algorithm that identifies anomalies by measuring how few splits are needed to isolate a data point. Points that require fewer splits are statistically unusual.

**Features** (10 total): AQI, PM2.5, PM10, CO, NO₂, SO₂, O₃, hour, day-of-week, month

**Contamination rate**: 5% — the model expects approximately 1 in 20 readings to be anomalous

**Behaviour**: A negative isolation score triggers an `anomaly_spike` alert, which appears in the frontend alert table. This catches readings that are unusual not just in absolute AQI value but in their multi-dimensional pollutant composition pattern.

**Storage**: Serialised as `{location_id}_anomaly.pkl`, co-located with forecast models

---

## API Reference

All endpoints are prefixed with `/api`. Interactive Swagger UI is available at `/docs`; ReDoc at `/redoc`.

### Locations

| Method | Path | Rate limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/api/locations` | 60/min | List all tracked cities with coordinates |
| `POST` | `/api/locations` | 10/min | Register a new city (city, country, lat, lon) |

### AQI

| Method | Path | Rate limit | Query params | Description |
|--------|------|-----------|-------------|-------------|
| `GET` | `/api/aqi/current` | 60/min | `city` | Latest reading, AQI value, and EPA health category |
| `GET` | `/api/aqi/history` | 30/min | `city`, `days` (1–90, default 7) | Time-series of historical readings |
| `GET` | `/api/aqi/pollutants` | 30/min | `city` | Latest PM2.5, PM10, CO, NO₂, SO₂, O₃ values |
| `GET` | `/api/aqi/forecast` | 30/min | `city` | Next 24 × hourly XGBoost predictions |

### Alerts

| Method | Path | Rate limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/api/alerts` | 60/min | All active alerts, newest first |
| `POST` | `/api/alerts/rules` | 10/min | Create a threshold rule (global or per-city) |
| `PATCH` | `/api/alerts/{id}/resolve` | 20/min | Mark an alert as resolved |

**Default threshold rules** (seeded at startup):

| Type | Threshold | EPA Category |
|------|-----------|-------------|
| `unhealthy` | AQI > 150 | Unhealthy |
| `very_unhealthy` | AQI > 200 | Very Unhealthy |
| `hazardous` | AQI > 300 | Hazardous |

### Analytics

| Method | Path | Rate limit | Query params | Description |
|--------|------|-----------|-------------|-------------|
| `GET` | `/api/analytics/city-comparison` | 30/min | — | Latest AQI snapshot for all cities side-by-side |
| `GET` | `/api/analytics/trends` | 30/min | `city`, `period` (daily/weekly/monthly) | Daily avg/min/max AQI over the period |
| `GET` | `/api/analytics/peak-hours` | 30/min | `city` | Average AQI grouped by hour of day (0–23) |
| `GET` | `/api/analytics/distribution` | 30/min | `city` | Count of readings per EPA health category |
| `GET` | `/api/analytics/gaps` | 30/min | `city`, `lookback_hours`, `threshold_minutes` | Gaps in the ingestion history exceeding a threshold |

### Health & Observability

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/live` | Liveness probe — returns 200 if the process is running |
| `GET` | `/ready` | Readiness probe — returns 503 if the database is unreachable |
| `GET` | `/health` | Deep health check: DB connectivity + scheduler job count |
| `GET` | `/metrics` | Prometheus metrics in text exposition format |

All responses include an `X-Request-ID` header. Pass a custom value via the `X-Request-ID` request header for end-to-end distributed tracing; otherwise a UUID is generated per request and propagated through all log lines.

---

## Security

The API ships with production-ready defaults requiring no additional configuration:

### HTTP Security Headers

Every response carries the following headers, injected by the `SecurityHeadersMiddleware`:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-sniffing attacks |
| `X-Frame-Options` | `DENY` | Blocks clickjacking via iframes |
| `Strict-Transport-Security` | `max-age=18000` | Enforces HTTPS on supporting browsers |
| `Permissions-Policy` | (restrictive) | Disables unused browser APIs (camera, mic, geolocation) |
| `Referrer-Policy` | `no-referrer` | Prevents referrer leakage |
| `Cache-Control` | `no-store` | Prevents sensitive API responses from being cached |

### Rate Limiting

Rate limits are enforced per IP address using slowapi. The limiter reads the `X-Forwarded-For` header set by nginx so client IPs are correctly identified even behind the proxy.

| Endpoint group | Limit |
|---------------|-------|
| Read endpoints (GET) | 30–60 requests/minute |
| Write endpoints (POST) | 10 requests/minute |
| Mutation endpoints (PATCH) | 20 requests/minute |

Clients that exceed the limit receive `429 Too Many Requests` with a `Retry-After` header.

### nginx Hardening

- `server_tokens off` — suppresses the nginx version from response headers and error pages
- `client_max_body_size 1m` — prevents oversized request bodies
- Proxy read/write timeouts of 30 seconds prevent slow-loris style attacks
- Gzip compression is applied only above 1024 bytes to prevent BREACH-style attacks on small responses

### Container Security

- The backend process runs as a non-root `appuser` (created in the Dockerfile)
- Multi-stage builds keep build tools (gcc, g++) out of the production image
- No secrets are baked into images; all credentials are injected at runtime via environment variables
- The application validates `DATABASE_URL` at startup and exits immediately with a clear error message if it is absent, preventing silent misconfiguration

### Email Alert Security

- SMTP credentials are optional; the application logs a warning and continues without email delivery if they are not provided
- Gmail App Passwords are used (not account passwords), limiting the scope of any credential compromise
- Alerts include a 60-minute deduplication window per city per alert type, preventing inbox flooding

---

## Monitoring & Observability

### Prometheus Metrics

The backend exposes a `/metrics` endpoint in Prometheus text format. Prometheus scrapes it every 15 seconds.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | `method`, `path`, `status_code` | Total HTTP requests served |
| `aqi_ingest_total` | Counter | `city`, `status` (`success`/`error`/`skipped`) | Ingestion attempt outcomes |
| `aqi_ingest_duration_seconds` | Histogram | — | End-to-end ingestion job duration |

Useful PromQL queries:

```promql
# HTTP error rate (5xx) over last 5 minutes
rate(http_requests_total{status_code=~"5.."}[5m])

# Ingestion success rate per city
rate(aqi_ingest_total{status="success"}[10m])

# p95 ingestion latency
histogram_quantile(0.95, rate(aqi_ingest_duration_seconds_bucket[10m]))
```

### Grafana Dashboard

The pre-built **AQI Platform** dashboard (`monitoring/grafana/dashboards/aqi.json`) is auto-provisioned on first Grafana start. It includes:

- HTTP request rate (rps)
- HTTP error rate (4xx + 5xx %)
- AQI ingest rate by city and status
- Ingest duration p50 / p95

Access at <http://localhost:3000> (admin / admin). Both the Prometheus datasource and the dashboard are configured automatically — no manual setup is required.

### Structured Logging

Logs use [structlog](https://www.structlog.org/) with two output formats:

- **Console** (dev, default): Coloured, human-readable output rendered with `ConsoleRenderer`
- **JSON** (production, set `LOG_FORMAT=json`): Structured JSON with all fields, suitable for ingestion by Datadog, Loki, or any log aggregator

Every log line emitted from the FastAPI middleware includes the `request_id` field, allowing a single trace ID to correlate all log lines — across ingestion, alert evaluation, and API handler — for a single inbound request.

---

## Database Schema

All tables use UUID primary keys, and all timestamps are stored as UTC datetimes with timezone awareness.

### `location`

| Column | Type | Constraints |
|--------|------|-------------|
| `location_id` | UUID | PK |
| `city` | VARCHAR(100) | NOT NULL |
| `country` | VARCHAR(100) | NOT NULL |
| `latitude` | NUMERIC(9,6) | NOT NULL |
| `longitude` | NUMERIC(9,6) | NOT NULL |
| `source` | VARCHAR(100) | default `"openweather"` |

### `air_quality_reading`

| Column | Type | Constraints |
|--------|------|-------------|
| `reading_id` | UUID | PK |
| `location_id` | UUID | FK → location, NOT NULL |
| `timestamp` | TIMESTAMPTZ | NOT NULL |
| `aqi` | INTEGER | NOT NULL |
| `pm25` | NUMERIC(8,2) | nullable |
| `pm10` | NUMERIC(8,2) | nullable |
| `co` | NUMERIC(8,2) | nullable |
| `no2` | NUMERIC(8,2) | nullable |
| `so2` | NUMERIC(8,2) | nullable |
| `o3` | NUMERIC(8,2) | nullable |
| `data_source` | VARCHAR(100) | default `"openweather"` |

Indexes: `ix_air_quality_location_timestamp (location_id, timestamp)`, unique constraint on `(location_id, timestamp)`.

### `alert`

| Column | Type | Constraints |
|--------|------|-------------|
| `alert_id` | UUID | PK |
| `location_id` | UUID | FK → location, NOT NULL |
| `alert_type` | VARCHAR(50) | NOT NULL — e.g. `"unhealthy"`, `"anomaly_spike"` |
| `threshold_value` | INTEGER | NOT NULL |
| `actual_aqi` | INTEGER | NOT NULL |
| `status` | VARCHAR(20) | default `"active"` — `active` or `resolved` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### `alert_rule`

| Column | Type | Constraints |
|--------|------|-------------|
| `rule_id` | UUID | PK |
| `location_id` | UUID | FK → location, nullable (NULL = global rule) |
| `alert_type` | VARCHAR(50) | NOT NULL |
| `threshold_value` | INTEGER | NOT NULL |
| `is_active` | BOOLEAN | default `true` |

### `aqi_prediction`

| Column | Type | Constraints |
|--------|------|-------------|
| `prediction_id` | UUID | PK |
| `location_id` | UUID | FK → location, NOT NULL |
| `prediction_time` | TIMESTAMPTZ | NOT NULL — when the forecast was generated |
| `forecast_for` | TIMESTAMPTZ | NOT NULL — the hour being predicted |
| `predicted_aqi` | NUMERIC(8,2) | NOT NULL |
| `model_name` | VARCHAR(100) | default `"xgboost"` |

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

Five containers start. Database migrations run automatically before the API server starts via `entrypoint.sh`.

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
| <http://localhost:5173> | Frontend (dev mode) |
| <http://localhost:80> | Frontend (production mode) |
| <http://localhost:8000/docs> | Interactive API docs (Swagger UI) |
| <http://localhost:8000/redoc> | ReDoc API reference |
| <http://localhost:9090> | Prometheus |
| <http://localhost:3000> | Grafana (admin / admin) |

The ingestion scheduler fires within 10 minutes of startup. AQI data and the world map populate automatically.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWEATHER_API_KEY` | Yes* | — | OpenWeather free-tier key (*warns on startup if missing) |
| `DATABASE_URL` | **Yes** | — | Full asyncpg connection string — app refuses to start without this |
| `POSTGRES_USER` | Yes | `aqi_user` | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password |
| `POSTGRES_DB` | Yes | `aqi_db` | Database name |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP port (STARTTLS) |
| `SMTP_USERNAME` | No | — | SMTP login (Gmail address) |
| `SMTP_PASSWORD` | No | — | Gmail App Password |
| `ALERT_EMAIL_FROM` | No | — | Sender address for alert emails |
| `ALERT_EMAIL_TO` | No | — | Comma-separated recipient list |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `LOG_FORMAT` | No | `console` | Set to `json` for structured production logging |

`DATABASE_URL` is validated at startup — the container exits immediately with a clear error message if it is not set, preventing silent misconfiguration.

---

## Tracked Cities

The seed script registers 12 cities across 6 continents:

| City | Country |
|------|---------|
| Colombo | Sri Lanka |
| London | United Kingdom |
| Delhi | India |
| New York | United States |
| Bangkok | Thailand |
| Tokyo | Japan |
| Paris | France |
| Sydney | Australia |
| Beijing | China |
| Cairo | Egypt |
| Mumbai | India |
| São Paulo | Brazil |

Additional cities can be registered at any time via `POST /api/locations`. The scheduler immediately begins ingesting data for newly registered cities on its next 10-minute tick.

---

## Scheduler Jobs

| Job ID | Schedule | Action |
|--------|----------|--------|
| `ingest_all_locations` | Every 10 minutes | Fetch OpenWeather → validate → AQI calc → deduplicate → persist → evaluate alert rules → anomaly check |
| `run_hourly_forecast` | Every 1 hour | Load 7 days of readings → engineer features → recursive 24-step XGBoost prediction → replace stored forecasts |
| `retrain_models_daily` | Daily at 02:00 UTC | Re-fit XGBoost + IsolationForest on last 30 days of readings per city → serialise to disk |

---

## Running Tests

### Unit tests (no database required)

```bash
cd backend
python -m pytest tests/test_ingestion.py tests/test_features.py -v
```

51 tests covering AQI calculation, EPA category mapping, reading validation (boundary conditions, negative values, out-of-range PM2.5), and feature-matrix construction.

### Integration tests (requires running PostgreSQL on port 5434)

```bash
docker exec aqi_backend python -m pytest tests/test_api.py -v
```

22 tests covering all API routes via in-process ASGI transport (no network round-trip). Tests run against a real PostgreSQL database to catch schema and query issues that mocks would miss.

### End-to-end smoke test (requires full stack running)

```bash
python scripts/smoke_test.py
```

23 checks: container health probes, all REST API endpoints, OpenAPI docs availability, and the frontend server response.

---

## CI/CD

GitHub Actions runs on every push to `main` and on every pull request.

### Backend job

1. Checkout code
2. Install Python 3.11 + dependencies (pip cache enabled)
3. `ruff check` — linting
4. `ruff format --check` — format compliance
5. `mypy app/ pipeline/` — static type checking
6. `pytest tests/test_ingestion.py tests/test_features.py` — unit tests (51 tests)

### Frontend job

1. Checkout code
2. Install Node 20 + dependencies (`npm ci`, cache enabled)
3. `tsc --noEmit` — TypeScript type checking
4. `npm run lint` — ESLint
5. `npm run build` — Vite production build (verifies the bundle compiles)

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers: aqi, alerts, analytics, locations
│   │   ├── ml/                # XGBoost forecasting + IsolationForest anomaly detection
│   │   ├── models/            # SQLAlchemy ORM models (5 tables)
│   │   ├── schemas/           # Pydantic v2 request/response schemas
│   │   ├── services/          # Ingestion, alert engine, ML orchestration, analytics
│   │   ├── seeds.py           # One-time city seed script (12 global cities)
│   │   ├── config.py          # pydantic-settings (.env parsing + validation)
│   │   ├── database.py        # Async SQLAlchemy engine (lazy-init) + session factory
│   │   ├── logging_config.py  # structlog setup (console dev / JSON prod)
│   │   ├── metrics.py         # Prometheus counters and histograms
│   │   ├── rate_limit.py      # slowapi limiter with X-Forwarded-For support
│   │   ├── security_headers.py  # OWASP security headers middleware
│   │   └── main.py            # FastAPI app, lifespan, middleware registration
│   ├── alembic/               # Database migration scripts
│   ├── models/                # Serialised ML model .pkl files (gitignored)
│   ├── pipeline/
│   │   └── scheduler.py       # APScheduler job definitions and cron schedules
│   ├── tests/                 # pytest unit + integration test suites
│   ├── Dockerfile             # Multi-stage build: builder (with gcc) → runtime (slim)
│   ├── entrypoint.sh          # alembic upgrade head → exec uvicorn
│   ├── pyproject.toml         # ruff + mypy configuration
│   └── requirements.txt       # Pinned Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # AQICard, AQIMap, TrendChart, PollutantChart,
│   │   │                      #   ForecastChart, AlertBanner, Navbar, Toast
│   │   ├── pages/             # Home, CityDashboard, Historical, Forecast, Alerts
│   │   ├── services/          # Typed Axios API client (api.ts)
│   │   └── utils/             # AQI → colour/category helpers
│   ├── Dockerfile             # Multi-stage: Node builder → nginx:alpine
│   ├── nginx.conf             # SPA fallback, /api proxy, gzip, asset caching
│   ├── vite.config.ts         # Vite bundler configuration
│   └── tsconfig.json          # TypeScript compiler options
├── monitoring/
│   ├── prometheus.yml         # Scrape config (15-second interval, 15-day retention)
│   └── grafana/
│       ├── dashboards/        # aqi.json — pre-built AQI platform dashboard
│       └── provisioning/      # Auto-configure datasource + dashboard on first start
├── scripts/
│   └── smoke_test.py          # End-to-end health check (23 assertions)
├── .github/
│   └── workflows/
│       └── ci.yml             # Backend + frontend CI jobs
├── docker-compose.yml         # Production service definitions with resource limits
├── docker-compose.override.yml  # Dev overrides: hot-reload, port 5434 exposure
├── .env.example               # Environment variable template
└── .pre-commit-config.yaml    # ruff, ESLint, YAML/JSON/large-file checks
```

---

## Development Notes

### Hot reload

Both backend (uvicorn `--reload`) and frontend (Vite HMR) reflect code changes without container restarts in development mode. The `docker-compose.override.yml` is applied automatically when running `docker-compose up` locally.

### Database migrations

After modifying a SQLAlchemy model, generate and apply a migration:

```bash
docker exec aqi_backend alembic revision --autogenerate -m "describe change"
docker exec aqi_backend alembic upgrade head
```

Migrations run automatically on every container start via [`entrypoint.sh`](backend/entrypoint.sh), so the schema is always up to date after a rebuild.

### Email alerts

Email delivery requires a Gmail App Password — not your account password. Generate one at <https://myaccount.google.com/apppasswords> and set `SMTP_PASSWORD` in `.env`. After changing `.env`:

```bash
docker-compose up -d --force-recreate backend
```

### Structured logging

Set `LOG_FORMAT=json` in `.env` for structured production logging. In dev the default console renderer uses colours when attached to a TTY. Every log line emitted from the FastAPI middleware includes `request_id` for correlation across the ingestion pipeline, alert engine, and HTTP layer.

### ML models

Models are serialised as `.pkl` files under `backend/models/` (gitignored). Cities with fewer than 5 readings skip the first forecast cycle — forecasts appear automatically as data accumulates. Models improve with each nightly retraining cycle as more historical data becomes available.

### Resource limits

Each container in `docker-compose.yml` declares explicit CPU and memory limits:

| Container | Memory | CPU |
|-----------|--------|-----|
| `aqi_db` | 512 MB | 0.5 |
| `aqi_backend` | 1 GB | 1.0 |
| `aqi_frontend` | 64 MB | 0.25 |
| `aqi_prometheus` | 256 MB | 0.25 |
| `aqi_grafana` | 256 MB | 0.25 |

These prevent any single service from starving the others on a development machine.
