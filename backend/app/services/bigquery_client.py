import asyncio
import io
import json
import logging
from datetime import datetime

from google.cloud import bigquery
from google.oauth2 import service_account

from app.config import settings

logger = logging.getLogger(__name__)

_client: bigquery.Client | None = None
_readings_buffer: list[dict] = []

_BQ_SCOPES = ["https://www.googleapis.com/auth/bigquery"]

BQ_PREDICTIONS_SCHEMA = [
    bigquery.SchemaField("prediction_id",  "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("location_id",    "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("city",           "STRING"),
    bigquery.SchemaField("country",        "STRING"),
    bigquery.SchemaField("prediction_time","TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("forecast_for",   "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("predicted_aqi",  "FLOAT",     mode="REQUIRED"),
    bigquery.SchemaField("model_name",     "STRING"),
]

BQ_SCHEMA = [
    bigquery.SchemaField("reading_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("location_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT"),
    bigquery.SchemaField("longitude", "FLOAT"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("aqi", "INTEGER"),
    bigquery.SchemaField("pm25", "FLOAT"),
    bigquery.SchemaField("pm10", "FLOAT"),
    bigquery.SchemaField("co", "FLOAT"),
    bigquery.SchemaField("no2", "FLOAT"),
    bigquery.SchemaField("so2", "FLOAT"),
    bigquery.SchemaField("o3", "FLOAT"),
    bigquery.SchemaField("temperature", "FLOAT"),
    bigquery.SchemaField("humidity", "FLOAT"),
    bigquery.SchemaField("wind_speed", "FLOAT"),
    bigquery.SchemaField("data_source", "STRING"),
]


def is_enabled() -> bool:
    return bool(settings.bigquery_project_id)


def _table_id() -> str:
    return f"{settings.bigquery_project_id}.{settings.bigquery_dataset_id}.air_quality_readings"


def _predictions_table_id() -> str:
    return f"{settings.bigquery_project_id}.{settings.bigquery_dataset_id}.aqi_predictions"


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        if settings.bigquery_credentials_json:
            info = json.loads(settings.bigquery_credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=_BQ_SCOPES
            )
            _client = bigquery.Client(
                project=settings.bigquery_project_id,
                credentials=credentials,
            )
        else:
            _client = bigquery.Client(project=settings.bigquery_project_id)
    return _client


def _ensure_sync() -> None:
    """Create the BigQuery dataset and table if they do not exist."""
    client = _get_client()
    project = settings.bigquery_project_id
    dataset_id = settings.bigquery_dataset_id

    dataset_ref = bigquery.DatasetReference(project, dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        ds = bigquery.Dataset(dataset_ref)
        ds.location = settings.bigquery_dataset_location
        client.create_dataset(ds, exists_ok=True)
        logger.info("Created BigQuery dataset %s.%s", project, dataset_id)

    table_ref = dataset_ref.table("air_quality_readings")
    try:
        client.get_table(table_ref)
        logger.info("BigQuery table %s already exists.", _table_id())
    except Exception:
        table = bigquery.Table(table_ref, schema=BQ_SCHEMA)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp",
        )
        table.clustering_fields = ["location_id"]
        client.create_table(table, exists_ok=True)
        logger.info("Created BigQuery table %s (partitioned by day, clustered by location_id).", _table_id())

    pred_ref = dataset_ref.table("aqi_predictions")
    try:
        client.get_table(pred_ref)
        logger.info("BigQuery table %s already exists.", _predictions_table_id())
    except Exception:
        pred_table = bigquery.Table(pred_ref, schema=BQ_PREDICTIONS_SCHEMA)
        pred_table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="forecast_for",
        )
        pred_table.clustering_fields = ["location_id"]
        client.create_table(pred_table, exists_ok=True)
        logger.info("Created BigQuery table %s (partitioned by forecast_for, clustered by location_id).", _predictions_table_id())


async def ensure_dataset_and_table() -> None:
    await asyncio.to_thread(_ensure_sync)


def _load_batch_sync(rows: list[dict], table_id: str, schema: list) -> None:
    """Batch-load rows via a BigQuery load job (free-tier compatible)."""
    client = _get_client()
    ndjson = "\n".join(json.dumps(r, default=str) for r in rows).encode("utf-8")
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_file(io.BytesIO(ndjson), table_id, job_config=job_config)
    job.result()
    if job.errors:
        logger.error("BigQuery batch load errors for %s: %s", table_id, job.errors)
    else:
        logger.info("BigQuery batch load: %d rows → %s", len(rows), table_id)


async def stream_reading(reading, location) -> None:
    """Buffer one reading. Call flush_readings() at end of ingestion cycle to commit."""
    if not is_enabled():
        return
    _readings_buffer.append({
        "reading_id": str(reading.reading_id),
        "location_id": str(reading.location_id),
        "city": location.city,
        "country": location.country,
        "latitude": float(location.latitude) if location.latitude is not None else None,
        "longitude": float(location.longitude) if location.longitude is not None else None,
        "timestamp": reading.timestamp.isoformat(),
        "aqi": int(reading.aqi) if reading.aqi is not None else None,
        "pm25": float(reading.pm25) if reading.pm25 is not None else None,
        "pm10": float(reading.pm10) if reading.pm10 is not None else None,
        "co": float(reading.co) if reading.co is not None else None,
        "no2": float(reading.no2) if reading.no2 is not None else None,
        "so2": float(reading.so2) if reading.so2 is not None else None,
        "o3": float(reading.o3) if reading.o3 is not None else None,
        "temperature": float(reading.temperature) if reading.temperature is not None else None,
        "humidity": float(reading.humidity) if reading.humidity is not None else None,
        "wind_speed": float(reading.wind_speed) if reading.wind_speed is not None else None,
        "data_source": reading.data_source,
    })


async def flush_readings() -> None:
    """Batch-load all buffered readings to BigQuery. One job per cycle — free-tier safe."""
    global _readings_buffer
    if not is_enabled() or not _readings_buffer:
        return
    rows = _readings_buffer[:]
    _readings_buffer = []
    try:
        await asyncio.to_thread(_load_batch_sync, rows, _table_id(), BQ_SCHEMA)
    except Exception as exc:
        logger.error("BigQuery readings flush failed: %s", exc)


def _run_query_sync(sql: str, params: list) -> list[dict]:
    client = _get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


async def run_query(sql: str, params: list | None = None) -> list[dict]:
    return await asyncio.to_thread(_run_query_sync, sql, params or [])


async def stream_predictions_rows(rows: list[dict]) -> None:
    """Batch-load prediction rows to BigQuery. Never raises — errors are logged."""
    if not is_enabled() or not rows:
        return
    try:
        await asyncio.to_thread(_load_batch_sync, rows, _predictions_table_id(), BQ_PREDICTIONS_SCHEMA)
    except Exception as exc:
        logger.error("Failed to load predictions to BigQuery: %s", exc)


def str_param(name: str, value: str) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "STRING", value)


def int_param(name: str, value: int) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "INT64", value)


def ts_param(name: str, value: datetime) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "TIMESTAMP", value)
