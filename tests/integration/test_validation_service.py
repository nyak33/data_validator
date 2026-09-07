from pathlib import Path

from openpyxl import Workbook

from data_validator.core.config import ValidationConfig
from data_validator.core.models import OverallStatus, ValidationMode
from data_validator.core.validation_service import ValidationService


def write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = ["SKU,Serial Number,QR Data"] + [",".join(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(paths, **kwargs):
    return ValidationService().validate(paths, ValidationConfig(**kwargs))


def test_clean_dataset_passes_and_preserves_source_bytes(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "0001", "QrA"), ("A", "0002", "QrB")])
    before = p.read_bytes()
    result = validate([p], serial_numeric_regex=r"(\d+)$")
    assert result.overall_status is OverallStatus.PASS
    assert result.record_count == 2
    assert p.read_bytes() == before


def test_full_detects_duplicate_serial_across_files(tmp_path: Path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_csv(a, [("A", "0001", "QrA")])
    write_csv(b, [("B", "0001", "QrB")])
    result = validate([a, b], mode=ValidationMode.FULL)
    assert result.overall_status is OverallStatus.FAIL
    assert result.count_code("DUPLICATE_SERIAL") == 1
    assert result.count_code("SERIAL_QR_CONFLICT") == 1
    issue = next(i for i in result.issues if i.code == "DUPLICATE_SERIAL")
    assert issue.source_file and issue.related_file


def test_quick_check_does_not_compare_different_files(tmp_path: Path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_csv(a, [("A", "0001", "QrA")])
    write_csv(b, [("B", "0001", "QrB")])
    result = validate([a, b], mode=ValidationMode.QUICK)
    assert result.overall_status is OverallStatus.PASS


def test_duplicate_complete_record_fails(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "0001", "QrA"), ("A", "0001", "QrA")])
    result = validate([p])
    assert result.count_code("DUPLICATE_RECORD") == 1
    assert result.overall_status is OverallStatus.FAIL


def test_duplicate_qr_and_qr_serial_conflict_fail(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "0001", "QrA"), ("A", "0002", "QrA")])
    result = validate([p])
    assert result.count_code("DUPLICATE_QR") == 1
    assert result.count_code("QR_SERIAL_CONFLICT") == 1


def test_qr_comparison_is_case_sensitive_by_default(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "0001", "AbC"), ("A", "0002", "abc")])
    result = validate([p])
    assert result.overall_status is OverallStatus.PASS


def test_missing_values_and_qr_surrounding_whitespace(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "", "QrA"), ("A", "0002", "")])
    with p.open("a", encoding="utf-8") as f:
        f.write('A,0003," QrC "\n')
    result = validate([p])
    assert result.count_code("MISSING_SERIAL") == 1
    assert result.count_code("MISSING_QR") == 1
    assert result.count_code("QR_SURROUNDING_WHITESPACE") == 1
    assert result.overall_status is OverallStatus.FAIL


def test_serial_format_range_gap_and_order_rules(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "SN0001", "Q1"), ("A", "SN0003", "Q3"), ("A", "SN0002", "Q2"), ("A", "BAD9", "Q9")])
    result = validate([p], serial_regex=r"SN\d{4}", serial_numeric_regex=r"(\d+)$", start_serial="SN0001", end_serial="SN0003")
    assert result.count_code("INVALID_SERIAL_FORMAT") == 1
    assert result.count_code("SERIAL_OUTSIDE_RANGE") == 1
    assert result.count_code("SERIAL_OUT_OF_ORDER") >= 1
    assert result.overall_status is OverallStatus.FAIL


def test_gap_is_warning_when_dataset_otherwise_clean(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "SN0001", "Q1"), ("A", "SN0003", "Q3")])
    result = validate([p], serial_regex=r"SN\d{4}", serial_numeric_regex=r"(\d+)$")
    assert result.count_code("SERIAL_GAP") == 1
    assert result.overall_status is OverallStatus.PASS_WITH_WARNINGS


def test_sku_and_quantity_rules(tmp_path: Path):
    p = tmp_path / "a.csv"
    write_csv(p, [("A", "0001", "Q1"), ("B", "0002", "Q2")])
    result = validate([p], one_sku_per_file=True, expected_sku="A", expected_rows_per_file=3, expected_batch_quantity=3)
    assert result.count_code("MIXED_SKU") == 1
    assert result.count_code("UNEXPECTED_SKU") == 1
    assert result.count_code("RECORD_COUNT_MISMATCH") == 1
    assert result.count_code("BATCH_QUANTITY_MISMATCH") == 1


def test_xlsx_input_preserves_text_serial_and_unicode(tmp_path: Path):
    p = tmp_path / "a.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["SKU", "Serial Number", "QR Data"])
    ws.append(["ទំនិញ", "0001", "QrA"])
    wb.save(p)
    result = validate([p])
    assert result.overall_status is OverallStatus.PASS
    assert result.record_count == 1


def test_required_column_missing_never_passes(tmp_path: Path):
    p = tmp_path / "a.csv"
    p.write_text("SKU,Serial Number\nA,0001\n", encoding="utf-8")
    result = validate([p])
    assert result.overall_status in {OverallStatus.FAIL, OverallStatus.INCOMPLETE}
    assert result.count_code("REQUIRED_COLUMN_MISSING") == 1


def test_corrupt_xlsx_never_passes(tmp_path: Path):
    p = tmp_path / "a.xlsx"
    p.write_bytes(b"broken")
    result = validate([p])
    assert result.overall_status is OverallStatus.INCOMPLETE
    assert result.count_code("CORRUPT_FILE") == 1
