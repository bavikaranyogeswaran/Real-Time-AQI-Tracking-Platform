import logging
import sys

import structlog


def configure_logging(log_format: str = "console") -> None:
    """Configure structlog to format all stdlib log records.

    log_format="json"    — newline-delimited JSON (production / log aggregators)
    log_format="console" — human-readable output (default / development)
    """
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    # Applied to foreign (stdlib) log records before the main processors.
    # _record is still in event_dict here, so add_logger_name can read record.name.
    pre_chain = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        # remove_processors_meta strips internal keys; renderer must be last.
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=pre_chain,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Configure native structlog loggers to feed into the same formatter.
    structlog.configure(
        processors=pre_chain
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
