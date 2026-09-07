from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import Severity, ValidationMode


@dataclass(slots=True)
class ColumnMapping:
    sku: str = "SKU"
    serial: str = "Serial Number"
    qr: str = "QR Data"


@dataclass(slots=True)
class ValidationConfig:
    columns: ColumnMapping = field(default_factory=ColumnMapping)
    mode: ValidationMode = ValidationMode.FULL
    batch_id: str = ""

    serial_trim_whitespace: bool = True
    serial_case_sensitive: bool = True
    serial_regex: str | None = None
    serial_prefix: str | None = None
    serial_total_length: int | None = None
    serial_numeric_regex: str | None = None

    qr_trim_whitespace: bool = False
    qr_case_sensitive: bool = True

    expected_sku: str | None = None
    one_sku_per_file: bool = False
    expected_rows_per_file: int | None = None
    expected_batch_quantity: int | None = None
    expected_quantity_per_sku: dict[str, int] = field(default_factory=dict)
    start_serial: str | None = None
    end_serial: str | None = None
    filename_regex: str | None = None

    gap_severity: Severity = Severity.WARNING
    out_of_order_severity: Severity = Severity.WARNING
    qr_whitespace_severity: Severity = Severity.WARNING
    filename_severity: Severity = Severity.WARNING

    memory_limit_mb: int | None = None
    threads: int | None = None
    temp_directory: Path | None = None
    csv_encoding: str = "utf-8-sig"
    csv_delimiter: str | None = None
    xlsx_sheet: str | None = None

    max_issue_details: int = 5_000
    max_gap_details: int = 5_000
    xlsx_batch_size: int = 20_000
