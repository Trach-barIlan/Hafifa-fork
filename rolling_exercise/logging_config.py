"""Centralized logging configuration for the Air Quality application."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


from config import settings

LOG_FILE = Path(settings.log_file)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Define log format
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "air_quality_api") -> logging.Logger:
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
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
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
