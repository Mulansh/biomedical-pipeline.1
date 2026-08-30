"""Structured logging configuration for Biomedical ETL Pipeline."""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "biomedical_pipeline", level: Optional[str] = "INFO") -> logging.Logger:
    """Configure and return a structured logger instance."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper() if level else "INFO", logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logger.level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()
