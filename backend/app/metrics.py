try:
    from prometheus_client import Counter, Histogram

    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status_code"],
    )

    aqi_ingest_total = Counter(
        "aqi_ingest_total",
        "Total AQI ingestion runs per city",
        ["city", "status"],
    )

    aqi_ingest_duration_seconds = Histogram(
        "aqi_ingest_duration_seconds",
        "Duration of one full location ingest cycle in seconds",
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

except ImportError:
    # No-op stubs so unit tests run without prometheus_client installed

    class _NoOpMetric:  # type: ignore[no-redef]
        def labels(self, **kwargs: object) -> "_NoOpMetric":
            return self

        def inc(self, amount: float = 1) -> None:
            pass

        def observe(self, value: float) -> None:
            pass

    http_requests_total = _NoOpMetric()  # type: ignore[assignment]
    aqi_ingest_total = _NoOpMetric()  # type: ignore[assignment]
    aqi_ingest_duration_seconds = _NoOpMetric()  # type: ignore[assignment]
