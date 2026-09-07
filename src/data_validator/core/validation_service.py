from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
import tempfile
import threading
import time

from data_validator.core.config import ValidationConfig
from data_validator.core.models import FileSummary, Severity, ValidationIssue, ValidationMode, ValidationResult
from data_validator.core.normalisation import extract_running_number, normalise_serial
from data_validator.ingestion.database import ValidationDatabase
from data_validator.ingestion.discovery import discover_files, discover_folder
from data_validator.ingestion.inspection import FileInspection, inspect_file
from data_validator.system.resources import choose_resource_plan, estimate_temp_bytes

ProgressCallback = Callable[[dict], None]


class ValidationCancelled(RuntimeError):
    pass


class ValidationService:
    def __init__(self) -> None:
        self._cancel = threading.Event()
        self._db: ValidationDatabase | None = None

    def cancel(self) -> None:
        self._cancel.set()
        if self._db is not None:
            self._db.interrupt()

    def validate(self, inputs: Iterable[Path | str], config: ValidationConfig | None = None, progress: ProgressCallback | None = None) -> ValidationResult:
        config = config or ValidationConfig()
        self._cancel.clear()
        result = ValidationResult(batch_id=config.batch_id, mode=config.mode)
        started = time.monotonic()
        db: ValidationDatabase | None = None
        try:
            files, ignored = self._resolve_inputs(inputs)
            result.file_count = len(files)
            result.metrics["ignored_files"] = [str(p) for p in ignored]
            if not files:
                result.incomplete = True
                result.add_issue(ValidationIssue("NO_SUPPORTED_FILES", Severity.FAIL, "No supported CSV/XLSX files were selected."))
                return result

            self._emit(progress, "Inspecting files", files_processed=0, total_files=len(files), records_processed=0)
            inspections = self._inspect_and_validate_structure(files, config, result, progress)
            if not inspections:
                if result.failure_count:
                    result.incomplete = True
                return result

            temp_dir = config.temp_directory or Path(tempfile.gettempdir())
            plan = choose_resource_plan(temp_dir, config.memory_limit_mb, config.threads)
            result.metrics["resource_plan"] = {
                "memory_limit_mb": plan.memory_limit_mb,
                "threads": plan.threads,
                "temp_directory": str(plan.temp_directory),
                "free_temp_bytes": plan.free_temp_bytes,
            }
            input_bytes = sum(info.path.stat().st_size for info in inspections)
            estimated_temp = estimate_temp_bytes(input_bytes)
            result.metrics["estimated_temp_bytes"] = estimated_temp
            if plan.free_temp_bytes < estimated_temp:
                result.incomplete = True
                result.add_issue(ValidationIssue(
                    "INSUFFICIENT_TEMP_DISK",
                    Severity.FAIL,
                    f"Insufficient temporary disk space. Estimated {estimated_temp:,} bytes required, {plan.free_temp_bytes:,} available.",
                ))
                return result

            db = ValidationDatabase(plan, config)
            self._db = db
            records = 0
            for idx, info in enumerate(inspections, start=1):
                self._check_cancel()
                self._emit(progress, "Importing data", files_processed=idx - 1, total_files=len(inspections), current_file=str(info.path), records_processed=records)
                summary = db.ingest(idx, info)
                records += summary.rows
                result.file_summaries.append(FileSummary(path=info.path, rows=summary.rows, file_id=idx))
                self._emit(progress, "Importing data", files_processed=idx, total_files=len(inspections), current_file=str(info.path), records_processed=records)

            result.record_count = records
            db.populate_serial_numbers()
            self._run_rules(db, config, result, progress)
            return result
        except ValidationCancelled:
            result.cancelled = True
            return result
        except Exception as exc:
            if self._cancel.is_set():
                result.cancelled = True
            else:
                result.incomplete = True
                result.add_issue(ValidationIssue("INTERNAL_ERROR", Severity.FAIL, f"Validation could not complete: {type(exc).__name__}: {exc}"))
            return result
        finally:
            result.metrics["elapsed_seconds"] = round(time.monotonic() - started, 3)
            if db is not None:
                db.close(cleanup=True)
            self._db = None

    def _resolve_inputs(self, inputs: Iterable[Path | str]) -> tuple[list[Path], list[Path]]:
        files: list[Path] = []
        ignored: list[Path] = []
        for item in inputs:
            p = Path(item).resolve()
            if p.is_dir():
                found = discover_folder(p, recursive=False)
            else:
                found = discover_files([p])
            files.extend(found.supported)
            ignored.extend(found.ignored)
        unique: dict[Path, None] = {}
        for p in files:
            unique[p] = None
        return list(unique), ignored

    def _inspect_and_validate_structure(self, files: list[Path], config: ValidationConfig, result: ValidationResult, progress: ProgressCallback | None) -> list[FileInspection]:
        good: list[FileInspection] = []
        required = {config.columns.sku, config.columns.serial, config.columns.qr}
        for idx, path in enumerate(files, start=1):
            self._check_cancel()
            info = inspect_file(path, encoding=config.csv_encoding, delimiter=config.csv_delimiter)
            if info.error:
                result.incomplete = True
                result.add_issue(ValidationIssue("CORRUPT_FILE", Severity.FAIL, info.error, source_file=str(path)))
            elif not info.has_data:
                result.add_issue(ValidationIssue("EMPTY_FILE", Severity.FAIL, "Selected file contains no data rows.", source_file=str(path)))
            else:
                missing = sorted(required.difference(info.headers))
                if missing:
                    result.incomplete = True
                    result.add_issue(ValidationIssue("REQUIRED_COLUMN_MISSING", Severity.FAIL, "Missing required column(s): " + ", ".join(missing), source_file=str(path)))
                else:
                    good.append(info)
            self._emit(progress, "Inspecting files", files_processed=idx, total_files=len(files), current_file=str(path), records_processed=0)
        return good

    def _run_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult, progress: ProgressCallback | None) -> None:
        rules: list[tuple[str, Callable[[], None]]] = [
            ("Checking required values", lambda: self._required_rules(db, config, result)),
            ("Checking Serial format", lambda: self._serial_format_rules(db, config, result)),
            ("Checking QR values", lambda: self._qr_rules(db, config, result)),
            ("Checking SKU", lambda: self._sku_rules(db, config, result)),
            ("Checking quantity", lambda: self._quantity_rules(db, config, result)),
            ("Checking duplicates", lambda: self._duplicate_rules(db, config, result)),
        ]
        if config.mode is ValidationMode.FULL:
            rules.extend([
                ("Checking Serial range", lambda: self._range_rules(db, config, result)),
                ("Checking Serial sequence", lambda: self._sequence_rules(db, config, result)),
            ])
        for stage, func in rules:
            self._check_cancel()
            self._emit(progress, stage, records_processed=result.record_count, files_processed=result.file_count, total_files=result.file_count)
            func()

    def _required_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        self._emit_row_rule(db, result, "MISSING_SERIAL", Severity.FAIL, "serial = ''", "Serial Number is missing.", config)
        self._emit_row_rule(db, result, "MISSING_QR", Severity.FAIL, "qr = ''", "QR Data is missing.", config)

    def _serial_format_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        conditions: list[str] = []
        params: list[object] = []
        if config.serial_regex:
            conditions.append("NOT regexp_full_match(serial, ?)")
            params.append(config.serial_regex)
        if config.serial_prefix:
            conditions.append("NOT starts_with(serial, ?)")
            params.append(config.serial_prefix if config.serial_case_sensitive else config.serial_prefix.upper())
        if config.serial_total_length is not None:
            conditions.append("length(serial) <> ?")
            params.append(config.serial_total_length)
        if config.serial_numeric_regex:
            conditions.append("serial_num IS NULL")
        if not conditions:
            return
        where = "serial <> '' AND (" + " OR ".join(conditions) + ")"
        self._emit_row_rule(db, result, "INVALID_SERIAL_FORMAT", Severity.FAIL, where, "Serial Number does not match configured format.", config, params)
        if config.serial_regex:
            suspicious_where = where + " AND regexp_matches(serial, '[OIl]')"
            self._emit_row_rule(db, result, "SUSPICIOUS_SERIAL_CHARACTER", Severity.WARNING, suspicious_where, "Serial contains a potentially ambiguous character.", config, params)

    def _qr_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        self._emit_row_rule(db, result, "QR_SURROUNDING_WHITESPACE", config.qr_whitespace_severity, "qr_raw IS NOT NULL AND qr_raw <> trim(qr_raw)", "QR Data has leading or trailing whitespace.", config)
        self._emit_row_rule(db, result, "QR_CONTROL_CHARACTER", Severity.FAIL, "qr_raw IS NOT NULL AND regexp_matches(qr_raw, '[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]')", "QR Data contains a control character.", config)
        self._emit_row_rule(db, result, "QR_LINEBREAK", Severity.FAIL, "qr_raw IS NOT NULL AND (contains(qr_raw, chr(10)) OR contains(qr_raw, chr(13)))", "QR Data contains a line break.", config)

    def _sku_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        if config.expected_sku is not None:
            self._emit_row_rule(db, result, "UNEXPECTED_SKU", Severity.FAIL, "sku <> ?", "Row contains an unexpected SKU.", config, [config.expected_sku])
        if config.one_sku_per_file:
            groups = db.conn.execute("SELECT file_id, min(source_file), count(DISTINCT sku) FROM records GROUP BY file_id HAVING count(DISTINCT sku) > 1").fetchall()
            for _, source_file, count in groups[: config.max_issue_details]:
                result.add_issue(ValidationIssue("MIXED_SKU", Severity.FAIL, f"File contains {count} different SKU values.", source_file=source_file))
            self._record_rule_count(result, "MIXED_SKU", len(groups))

    def _quantity_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        if config.expected_rows_per_file is not None:
            rows = db.conn.execute("SELECT file_id, min(source_file), count(*) FROM records GROUP BY file_id").fetchall()
            mismatches = [(fid, path, count) for fid, path, count in rows if int(count) != config.expected_rows_per_file]
            for _, path, count in mismatches[: config.max_issue_details]:
                result.add_issue(ValidationIssue("RECORD_COUNT_MISMATCH", Severity.FAIL, f"Expected {config.expected_rows_per_file:,} rows, found {int(count):,}.", source_file=path))
            self._record_rule_count(result, "RECORD_COUNT_MISMATCH", len(mismatches))
        if config.mode is ValidationMode.FULL and config.expected_batch_quantity is not None and result.record_count != config.expected_batch_quantity:
            result.add_issue(ValidationIssue("BATCH_QUANTITY_MISMATCH", Severity.FAIL, f"Expected batch quantity {config.expected_batch_quantity:,}, found {result.record_count:,}."))
            self._record_rule_count(result, "BATCH_QUANTITY_MISMATCH", 1)

    def _duplicate_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        group_select = "file_id, " if config.mode is ValidationMode.QUICK else ""
        group_by = "file_id, " if config.mode is ValidationMode.QUICK else ""
        exact = db.conn.execute(f"SELECT {group_select} serial, qr, count(*) FROM records WHERE serial <> '' AND qr <> '' GROUP BY {group_by} serial, qr HAVING count(*) > 1 ORDER BY serial, qr").fetchall()
        for row in exact[: config.max_issue_details]:
            if config.mode is ValidationMode.QUICK:
                file_id, serial, qr, n = row
            else:
                file_id = None
                serial, qr, n = row
            first, second = self._first_two(db, serial=serial, qr=qr, file_id=file_id)
            result.add_issue(self._group_issue("DUPLICATE_RECORD", "The same Serial/QR pair appears more than once.", serial, qr, first, second, n))
        self._record_rule_count(result, "DUPLICATE_RECORD", len(exact))

        serial_groups = db.conn.execute(f"SELECT {group_select} serial, count(DISTINCT qr) FROM records WHERE serial <> '' AND qr <> '' GROUP BY {group_by} serial HAVING count(DISTINCT qr) > 1 ORDER BY serial").fetchall()
        for row in serial_groups[: config.max_issue_details]:
            if config.mode is ValidationMode.QUICK:
                file_id, serial, distinct_qr = row
            else:
                file_id = None
                serial, distinct_qr = row
            first, second = self._first_two(db, serial=serial, file_id=file_id, distinct_qr=True)
            for code, message in (("DUPLICATE_SERIAL", "Serial Number is associated with multiple QR values."), ("SERIAL_QR_CONFLICT", "One Serial maps to more than one QR value.")):
                result.add_issue(self._group_issue(code, message, serial, None, first, second, distinct_qr))
        self._record_rule_count(result, "DUPLICATE_SERIAL", len(serial_groups))
        self._record_rule_count(result, "SERIAL_QR_CONFLICT", len(serial_groups))

        qr_groups = db.conn.execute(f"SELECT {group_select} qr, count(DISTINCT serial) FROM records WHERE serial <> '' AND qr <> '' GROUP BY {group_by} qr HAVING count(DISTINCT serial) > 1 ORDER BY qr").fetchall()
        for row in qr_groups[: config.max_issue_details]:
            if config.mode is ValidationMode.QUICK:
                file_id, qr, distinct_serial = row
            else:
                file_id = None
                qr, distinct_serial = row
            first, second = self._first_two(db, qr=qr, file_id=file_id, distinct_serial=True)
            for code, message in (("DUPLICATE_QR", "QR Data is associated with multiple Serial Numbers."), ("QR_SERIAL_CONFLICT", "One QR value maps to more than one Serial Number.")):
                result.add_issue(self._group_issue(code, message, None, qr, first, second, distinct_serial))
        self._record_rule_count(result, "DUPLICATE_QR", len(qr_groups))
        self._record_rule_count(result, "QR_SERIAL_CONFLICT", len(qr_groups))

    def _range_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        if not config.start_serial and not config.end_serial:
            return
        if not config.serial_numeric_regex:
            result.incomplete = True
            result.add_issue(ValidationIssue("INVALID_CONFIGURATION", Severity.FAIL, "Serial range requires serial_numeric_regex."))
            return
        low = extract_running_number(normalise_serial(config.start_serial or "", config), config) if config.start_serial else None
        high = extract_running_number(normalise_serial(config.end_serial or "", config), config) if config.end_serial else None
        if (config.start_serial and low is None) or (config.end_serial and high is None):
            result.incomplete = True
            result.add_issue(ValidationIssue("INVALID_CONFIGURATION", Severity.FAIL, "Configured Serial range could not be parsed."))
            return
        outside: list[str] = []
        params: list[object] = []
        if low is not None:
            outside.append("serial_num < ?")
            params.append(low)
        if high is not None:
            outside.append("serial_num > ?")
            params.append(high)
        where = "serial_num IS NOT NULL AND (" + " OR ".join(outside) + ")"
        self._emit_row_rule(db, result, "SERIAL_OUTSIDE_RANGE", Severity.FAIL, where, "Serial Number is outside the configured range.", config, params)

    def _sequence_rules(self, db: ValidationDatabase, config: ValidationConfig, result: ValidationResult) -> None:
        if not config.serial_numeric_regex:
            return
        gaps = db.conn.execute("""
            WITH distinct_values AS (
                SELECT DISTINCT regexp_replace(serial, ?, '') AS seq_key, serial_num
                FROM records WHERE serial_num IS NOT NULL
            ), ordered AS (
                SELECT seq_key, serial_num, lead(serial_num) OVER (PARTITION BY seq_key ORDER BY serial_num) AS next_num
                FROM distinct_values
            )
            SELECT seq_key, serial_num + 1, next_num - 1, next_num - serial_num - 1
            FROM ordered WHERE next_num > serial_num + 1
            ORDER BY seq_key, serial_num
        """, [config.serial_numeric_regex]).fetchall()
        for seq_key, start, end, count in gaps[: config.max_gap_details]:
            result.add_issue(ValidationIssue("SERIAL_GAP", config.gap_severity, f"Serial sequence has a gap: {int(start)} to {int(end)} ({int(count):,} missing).", metadata={"sequence_key": seq_key, "missing_start": int(start), "missing_end": int(end), "missing_count": int(count)}))
        self._record_rule_count(result, "SERIAL_GAP", len(gaps))
        result.metrics["missing_serial_count"] = int(sum(int(row[3]) for row in gaps))

        ordered = db.conn.execute("""
            WITH x AS (
                SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw, serial_num,
                       lag(serial_num) OVER (PARTITION BY file_id ORDER BY source_row) AS previous_num
                FROM records WHERE serial_num IS NOT NULL
            )
            SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw, previous_num, serial_num
            FROM x WHERE previous_num IS NOT NULL AND serial_num < previous_num
            ORDER BY source_file, source_row
        """).fetchall()
        for row in ordered[: config.max_issue_details]:
            source_file, sheet, source_row, sku, serial, qr, previous, current = row
            result.add_issue(ValidationIssue("SERIAL_OUT_OF_ORDER", config.out_of_order_severity, f"Serial running number decreased from {int(previous)} to {int(current)}.", source_file=source_file, source_sheet=sheet, source_row=int(source_row), sku=sku, serial=serial, qr=qr))
        self._record_rule_count(result, "SERIAL_OUT_OF_ORDER", len(ordered))

    def _emit_row_rule(self, db: ValidationDatabase, result: ValidationResult, code: str, severity: Severity, where: str, message: str, config: ValidationConfig, params: list[object] | None = None) -> None:
        params = params or []
        count = int(db.conn.execute(f"SELECT count(*) FROM records WHERE {where}", params).fetchone()[0])
        self._record_rule_count(result, code, count)
        if not count:
            return
        rows = db.conn.execute(f"SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw FROM records WHERE {where} ORDER BY file_id, source_row LIMIT {int(config.max_issue_details)}", params).fetchall()
        for source_file, sheet, source_row, sku, serial, qr in rows:
            result.add_issue(ValidationIssue(code, severity, message, source_file=source_file, source_sheet=sheet, source_row=int(source_row), sku=sku, serial=serial, qr=qr))

    def _first_two(self, db: ValidationDatabase, *, serial: str | None = None, qr: str | None = None, file_id: int | None = None, distinct_qr: bool = False, distinct_serial: bool = False) -> tuple[tuple | None, tuple | None]:
        clauses: list[str] = []
        params: list[object] = []
        if serial is not None:
            clauses.append("serial = ?")
            params.append(serial)
        if qr is not None:
            clauses.append("qr = ?")
            params.append(qr)
        if file_id is not None:
            clauses.append("file_id = ?")
            params.append(file_id)
        where = " AND ".join(clauses)
        if distinct_qr:
            sql = f"SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw FROM (SELECT *, row_number() OVER (PARTITION BY qr ORDER BY file_id, source_row) AS rn FROM records WHERE {where}) WHERE rn = 1 ORDER BY source_file, source_row LIMIT 2"
        elif distinct_serial:
            sql = f"SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw FROM (SELECT *, row_number() OVER (PARTITION BY serial ORDER BY file_id, source_row) AS rn FROM records WHERE {where}) WHERE rn = 1 ORDER BY source_file, source_row LIMIT 2"
        else:
            sql = f"SELECT source_file, source_sheet, source_row, sku_raw, serial_raw, qr_raw FROM records WHERE {where} ORDER BY file_id, source_row LIMIT 2"
        rows = db.conn.execute(sql, params).fetchall()
        return rows[0] if rows else None, rows[1] if len(rows) > 1 else None

    def _group_issue(self, code: str, message: str, serial: str | None, qr: str | None, first: tuple | None, second: tuple | None, n: int) -> ValidationIssue:
        first = first or (None, None, None, None, serial, qr)
        second = second or (None, None, None, None, None, None)
        return ValidationIssue(code, Severity.FAIL, message, source_file=first[0], source_sheet=first[1], source_row=int(first[2]) if first[2] is not None else None, sku=first[3], serial=serial or first[4], qr=qr or first[5], related_file=second[0], related_row=int(second[2]) if second[2] is not None else None, metadata={"occurrence_count": int(n)})

    def _record_rule_count(self, result: ValidationResult, code: str, count: int) -> None:
        result.metrics.setdefault("rule_counts", {})[code] = int(count)

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise ValidationCancelled()

    def _emit(self, callback: ProgressCallback | None, stage: str, **values) -> None:
        if callback:
            callback({"stage": stage, **values})
