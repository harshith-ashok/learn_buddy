import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from src.core.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure root logging once, as structured JSON to stdout.

    Idempotent: safe to call from both the app entrypoint and test setup.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "{levelname}{name}{message}{asctime}",
            style="{",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    for noisy_logger in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(noisy_logger).handlers = [handler]

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger; configures logging on first use."""
    configure_logging()
    return logging.getLogger(name)
