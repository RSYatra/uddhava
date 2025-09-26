"""
Production-grade logging configuration.

This module provides structured logging with proper formatters,
handlers, and configuration for different environments.
"""

import logging
import logging.config
import sys
import time
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up structured logging with:
    - JSON formatting for production
    - Colored console output for development
    - File rotation for persistent logs
    - Different log levels per component
    """

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": (
                    "[{asctime}] {levelname:8} {name:25} {funcName:15} "
                    "{lineno:4d} | {message}"
                ),
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "{levelname:8} | {message}",
                "style": "{",
            },
            "json": (
                {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": (
                        "%(asctime)s %(name)s %(levelname)s "
                        "%(funcName)s %(lineno)d %(message)s"
                    ),
                }
                if settings.is_production
                else {
                    "format": "[{asctime}] {levelname:8} {name:25} | {message}",
                    "style": "{",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            ),
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO" if settings.is_production else "DEBUG",
                "formatter": "json" if settings.is_production else "detailed",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json" if settings.is_production else "detailed",
                "filename": log_dir / "app.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json" if settings.is_production else "detailed",
                "filename": log_dir / "errors.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 10,
                "encoding": "utf8",
            },
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": "DEBUG" if settings.debug else "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.api": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.db": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.services": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # Third-party loggers
            "sqlalchemy.engine": {
                "level": "WARN" if settings.is_production else "INFO",
                "handlers": ["file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": (["file"] if settings.is_production else ["console"]),
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console", "error_file"],
        },
    }

    logging.config.dictConfig(config)

    # Log startup information
    logger = logging.getLogger("app")
    logger.info("=" * 50)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Log directory: {log_dir.absolute()}")
    logger.info("=" * 50)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"app.{name.replace('app.', '')}")


# Context manager for logging execution time
class LogExecutionTime:
    """Context manager to log execution time of operations."""

    def __init__(
        self, logger: logging.Logger, operation: str, level: int = logging.INFO
    ):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            self.logger.error(
                f"{self.operation} failed after {duration:.3f}s: {exc_val}"
            )
        else:
            self.logger.log(
                self.level, f"{self.operation} completed in {duration:.3f}s"
            )
