from __future__ import annotations

import argparse
import csv
from pathlib import Path


def generate_csv(
    output: Path,
    rows: int,
    *,
    sku_count: int = 11,
    serial_prefix: str = "S",
    serial_width: int = 12,
    qr_prefix: str = "QR-",
    duplicate_serial_at: int | None = None,
    duplicate_qr_at: int | None = None,
    missing_serial_at: int | None = None,
    missing_qr_at: int | None = None,
    gap_after: int | None = None,
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SKU", "Serial Number", "QR Data"])
        offset = 0
        for index in range(1, rows + 1):
            if gap_after is not None and index > gap_after:
                offset = 1
            number = index + offset
            serial = f"{serial_prefix}{number:0{serial_width}d}"
            qr = f"{qr_prefix}{number:0{serial_width}d}"
            sku = f"SKU{((index - 1) % max(1, sku_count)) + 1:02d}"
            if duplicate_serial_at is not None and index == duplicate_serial_at and index > 1:
                serial = f"{serial_prefix}{1:0{serial_width}d}"
            if duplicate_qr_at is not None and index == duplicate_qr_at and index > 1:
                qr = f"{qr_prefix}{1:0{serial_width}d}"
            if missing_serial_at is not None and index == missing_serial_at:
                serial = ""
            if missing_qr_at is not None and index == missing_qr_at:
                qr = ""
            writer.writerow([sku, serial, qr])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic Data Validator input.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--sku-count", type=int, default=11)
    parser.add_argument("--duplicate-serial-at", type=int)
    parser.add_argument("--duplicate-qr-at", type=int)
    parser.add_argument("--missing-serial-at", type=int)
    parser.add_argument("--missing-qr-at", type=int)
    parser.add_argument("--gap-after", type=int)
    args = parser.parse_args()
    generate_csv(
        args.output,
        args.rows,
        sku_count=args.sku_count,
        duplicate_serial_at=args.duplicate_serial_at,
        duplicate_qr_at=args.duplicate_qr_at,
        missing_serial_at=args.missing_serial_at,
        missing_qr_at=args.missing_qr_at,
        gap_after=args.gap_after,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
