from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import tempfile


def default_log_directory() -> Path:
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "DataValidator" / "logs"
    return Path(tempfile.gettempdir()) / "DataValidator" / "logs"


def configure_logging(log_directory: Path | None = None) -> Path:
    directory = Path(log_directory or default_log_directory())
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "data-validator.log"
    root = logging.getLogger("data_validator")
    root.setLevel(logging.INFO)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
    return log_path
