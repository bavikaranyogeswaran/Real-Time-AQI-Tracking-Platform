import asyncio
import json
import logging
from datetime import datetime

from google.cloud import bigquery
from google.oauth2 import service_account

from app.config import settings

logger = logging.getLogger(__name__)

_client: bigquery.Client | None = None

_BQ_SCOPES = ["https://www.googleapis.com/auth/bigquery"]

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
        ds.location = "US"
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


async def ensure_dataset_and_table() -> None:
    await asyncio.to_thread(_ensure_sync)


def _stream_row_sync(row: dict) -> None:
    client = _get_client()
    errors = client.insert_rows_json(_table_id(), [row])
    if errors:
        logger.error("BigQuery streaming insert errors: %s", errors)


async def stream_reading(reading, location) -> None:
    """Stream one AirQualityReading to BigQuery. Never raises — errors are logged."""
    if not is_enabled():
        return
    row = {
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
    }
    try:
        await asyncio.to_thread(_stream_row_sync, row)
        logger.debug("Streamed reading %s to BigQuery.", reading.reading_id)
    except Exception as exc:
        logger.error("Failed to stream reading to BigQuery: %s", exc)


def _run_query_sync(sql: str, params: list) -> list[dict]:
    client = _get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


async def run_query(sql: str, params: list | None = None) -> list[dict]:
    return await asyncio.to_thread(_run_query_sync, sql, params or [])


def str_param(name: str, value: str) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "STRING", value)


def int_param(name: str, value: int) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "INT64", value)


def ts_param(name: str, value: datetime) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "TIMESTAMP", value)
