from __future__ import annotations

import re

from .config import ValidationConfig


def normalise_serial(value: object, config: ValidationConfig) -> str:
    text = "" if value is None else str(value)
    if config.serial_trim_whitespace:
        text = text.strip()
    if not config.serial_case_sensitive:
        text = text.upper()
    return text


def normalise_qr(value: object, config: ValidationConfig) -> str:
    text = "" if value is None else str(value)
    if config.qr_trim_whitespace:
        text = text.strip()
    if not config.qr_case_sensitive:
        text = text.upper()
    return text


def extract_running_number(serial: str, config: ValidationConfig) -> int | None:
    if not config.serial_numeric_regex:
        return None
    match = re.search(config.serial_numeric_regex, serial)
    if not match:
        return None
    try:
        value = match.group(1) if match.lastindex else match.group(0)
        return int(value)
    except (ValueError, IndexError):
        return None
