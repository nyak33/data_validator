from pathlib import Path

from openpyxl import Workbook

from data_validator.ingestion.inspection import inspect_file


def test_inspect_csv_preserves_unicode_headers_and_detects_data(tmp_path: Path):
    path = tmp_path / "sample.csv"
    path.write_text("SKU,Serial Number,QR Data\nទំនិញ,00123,AbC\n", encoding="utf-8")
    info = inspect_file(path)
    assert info.headers == ["SKU", "Serial Number", "QR Data"]
    assert info.has_data is True
    assert info.error is None


def test_inspect_csv_header_only_is_empty(tmp_path: Path):
    path = tmp_path / "empty.csv"
    path.write_text("SKU,Serial Number,QR Data\n", encoding="utf-8")
    info = inspect_file(path)
    assert info.has_data is False


def test_inspect_xlsx_reads_first_sheet_headers(tmp_path: Path):
    path = tmp_path / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(["SKU", "Serial Number", "QR Data"])
    ws.append(["A", "0001", "Qr01"])
    wb.save(path)
    info = inspect_file(path)
    assert info.headers == ["SKU", "Serial Number", "QR Data"]
    assert info.sheet == "Data"
    assert info.has_data is True


def test_corrupt_xlsx_returns_error_not_exception(tmp_path: Path):
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"not an excel workbook")
    info = inspect_file(path)
    assert info.error
