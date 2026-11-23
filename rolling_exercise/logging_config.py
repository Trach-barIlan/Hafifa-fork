"""Centralized logging configuration for the Air Quality application."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings
from constants import (
    DATE_FORMAT,
    DEFAULT_LOGGER_NAME,
    LOG_BACKUP_COUNT,
    LOG_FORMAT,
    LOG_MAX_BYTES,
)

LOG_FILE = Path(settings.log_file)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Configure and return an application logger with console and file handlers.

    Args:
        name: Name of the logger instance.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if not logger.handlers:
        logger.setLevel(level)

        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

        # Rotating File Handler (for preventing unbounded space usage, max 5MB with 5 backups)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console Handler (for dev output)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
