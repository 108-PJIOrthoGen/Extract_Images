"""Logging utilities."""

import logging
import sys


def setup_logger(name: str = "extractor") -> logging.Logger:
    """Configure standard logger for the project."""
    logger = logging.getLogger(name)

    # Only configure if logger has no handlers to avoid duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
