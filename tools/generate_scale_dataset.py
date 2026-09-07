from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import math
from pathlib import Path

import duckdb


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _default_error_positions(rows: int) -> dict[str, int]:
    if rows < 20:
        raise ValueError("At least 20 rows are required when injected errors are enabled.")
    return {
        "duplicate_serial_at": rows // 4,
        "duplicate_qr_at": rows // 2,
        "duplicate_record_at": (rows * 3) // 4,
        "missing_serial_at": rows - 1,
        "missing_qr_at": rows,
    }


def generate_partitioned_csv(
    output_dir: Path,
    *,
    rows: int = 260_000_000,
    rows_per_file: int = 1_000_000,
    sku_count: int = 11,
    inject_errors: bool = True,
    overwrite: bool = False,
    threads: int | None = None,
) -> dict[str, object]:
    """Generate a deterministic, partitioned CSV dataset for full-scale validation tests."""
    if rows <= 0:
        raise ValueError("rows must be greater than zero")
    if rows_per_file <= 0:
        raise ValueError("rows_per_file must be greater than zero")
    if sku_count <= 0:
        raise ValueError("sku_count must be greater than zero")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_parts = list(output_dir.glob("part_*.csv"))
    manifest_path = output_dir / "manifest.json"
    if (existing_parts or manifest_path.exists()) and not overwrite:
        raise FileExistsError(
            f"Generated dataset already exists in {output_dir}. Use --overwrite to replace it."
        )
    if overwrite:
        for path in existing_parts:
            path.unlink()
        manifest_path.unlink(missing_ok=True)

    injected_errors = _default_error_positions(rows) if inject_errors else {}
    file_count = math.ceil(rows / rows_per_file)
    connection = duckdb.connect()
    try:
        if threads is not None:
            connection.execute(f"SET threads = {max(1, int(threads))}")

        for part_index in range(file_count):
            start = part_index * rows_per_file + 1
            end = min(rows, start + rows_per_file - 1)
            sku = f"SKU{(part_index % sku_count) + 1:02d}"
            output_file = output_dir / f"part_{part_index + 1:04d}_{sku}.csv"

            serial_base = "'S' || lpad(CAST(i AS VARCHAR), 12, '0')"
            qr_base = "'QR-' || lpad(CAST(i AS VARCHAR), 12, '0')"
            serial_expr = serial_base
            qr_expr = qr_base

            if inject_errors:
                duplicate_serial_at = injected_errors["duplicate_serial_at"]
                duplicate_qr_at = injected_errors["duplicate_qr_at"]
                duplicate_record_at = injected_errors["duplicate_record_at"]
                missing_serial_at = injected_errors["missing_serial_at"]
                missing_qr_at = injected_errors["missing_qr_at"]
                serial_expr = f"""
                    CASE
                        WHEN i = {duplicate_serial_at} THEN 'S000000000001'
                        WHEN i = {duplicate_record_at} THEN 'S000000000003'
                        WHEN i = {missing_serial_at} THEN ''
                        ELSE {serial_base}
                    END
                """
                qr_expr = f"""
                    CASE
                        WHEN i = {duplicate_qr_at} THEN 'QR-000000000002'
                        WHEN i = {duplicate_record_at} THEN 'QR-000000000003'
                        WHEN i = {missing_qr_at} THEN ''
                        ELSE {qr_base}
                    END
                """

            connection.execute(
                f"""
                COPY (
                    SELECT
                        {_sql_string(sku)} AS "SKU",
                        {serial_expr} AS "Serial Number",
                        {qr_expr} AS "QR Data"
                    FROM range({start}, {end + 1}) AS generated(i)
                ) TO {_sql_string(output_file.as_posix())}
                (HEADER, DELIMITER ',')
                """
            )
            print(
                f"Generated {output_file.name}: {end - start + 1:,} rows "
                f"({end:,}/{rows:,})"
            )
    finally:
        connection.close()

    manifest: dict[str, object] = {
        "dataset": "Data Validator synthetic scale dataset",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_rows": rows,
        "rows_per_file": rows_per_file,
        "file_count": file_count,
        "sku_count": sku_count,
        "serial_format": "S + 12 digit running number",
        "qr_format": "QR- + 12 digit running number",
        "injected_errors": injected_errors,
        "recommended_validation_settings": {
            "mode": "FULL",
            "serial_regex": r"S\d{12}",
            "serial_numeric_regex": r"(\d+)$",
            "expected_rows_per_file": rows_per_file if rows % rows_per_file == 0 else None,
            "expected_batch_quantity": rows,
            "start_serial": "S000000000001",
            "end_serial": f"S{rows:012d}",
            "one_sku_per_file": True,
        },
        "expected_injected_findings": (
            {
                "DUPLICATE_SERIAL": 1,
                "SERIAL_QR_CONFLICT": 1,
                "DUPLICATE_QR": 1,
                "QR_SERIAL_CONFLICT": 1,
                "DUPLICATE_RECORD": 1,
                "MISSING_SERIAL": 1,
                "MISSING_QR": 1,
            }
            if inject_errors
            else {}
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a partitioned large-scale CSV dataset for Data Validator testing."
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--rows", type=int, default=260_000_000)
    parser.add_argument("--rows-per-file", type=int, default=1_000_000)
    parser.add_argument("--sku-count", type=int, default=11)
    parser.add_argument("--clean", action="store_true", help="Generate no deliberate validation errors.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--threads", type=int)
    args = parser.parse_args()

    manifest = generate_partitioned_csv(
        args.output_dir,
        rows=args.rows,
        rows_per_file=args.rows_per_file,
        sku_count=args.sku_count,
        inject_errors=not args.clean,
        overwrite=args.overwrite,
        threads=args.threads,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
