import structlog
import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger
from backend.config.settings import settings


def configure_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()
            if settings.DEBUG
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    file_handler = logging.FileHandler(
        logs_dir / "portfolio_manager.log", encoding="utf-8"
    )
    file_handler.setLevel(log_level)

    if settings.DEBUG:
        console_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    else:
        console_fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )

    console_handler.setFormatter(console_fmt)
    file_handler.setFormatter(console_fmt)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    for lib in ("uvicorn", "uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    structlog.get_logger(__name__).info(
        "logging configured",
        level=settings.LOG_LEVEL,
        debug=settings.DEBUG,
    )
