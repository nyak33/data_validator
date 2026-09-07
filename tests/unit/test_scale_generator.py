import csv
import json
from pathlib import Path

from tools.generate_scale_dataset import generate_partitioned_csv


def test_generate_partitioned_csv_creates_exact_row_count_and_manifest(tmp_path: Path) -> None:
    output = tmp_path / "scale"

    manifest = generate_partitioned_csv(
        output,
        rows=20,
        rows_per_file=7,
        sku_count=3,
        inject_errors=True,
    )

    files = sorted(output.glob("part_*.csv"))
    assert len(files) == 3
    assert manifest["total_rows"] == 20
    assert manifest["file_count"] == 3
    assert manifest["rows_per_file"] == 7

    data_rows = 0
    rows: dict[int, tuple[str, str, str]] = {}
    for path in files:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                data_rows += 1
                rows[data_rows] = (row["SKU"], row["Serial Number"], row["QR Data"])

    assert data_rows == 20
    assert rows[1][1:] == ("S000000000001", "QR-000000000001")
    assert rows[5][1] == rows[1][1]  # duplicate Serial, different QR
    assert rows[10][2] == rows[2][2]  # duplicate QR, different Serial
    assert rows[15][1:] == rows[3][1:]  # exact duplicate pair
    assert rows[19][1] == ""
    assert rows[20][2] == ""

    saved = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert saved["total_rows"] == 20
    assert saved["injected_errors"]["duplicate_serial_at"] == 5
