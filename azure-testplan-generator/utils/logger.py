"""Centralized logger configuration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import logging


def setup_logger(logs_dir: str = "logs") -> tuple[logging.Logger, Path]:
    """Create and configure logger per execution."""
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_path / f"execution_{timestamp}.log"

    logger = logging.getLogger("azure_testplan_generator")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, log_file

