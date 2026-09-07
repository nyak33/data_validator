from pathlib import Path

from data_validator.ingestion.discovery import discover_files, discover_folder


def test_discover_folder_does_not_recurse_by_default(tmp_path: Path):
    (tmp_path / "a.csv").write_text("SKU,Serial Number,QR Data\n", encoding="utf-8")
    (tmp_path / "b.xlsx").write_bytes(b"not-real")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    nested = tmp_path / "old"
    nested.mkdir()
    (nested / "c.csv").write_text("SKU,Serial Number,QR Data\n", encoding="utf-8")
    result = discover_folder(tmp_path)
    assert [p.name for p in result.supported] == ["a.csv", "b.xlsx"]
    assert [p.name for p in result.ignored] == ["notes.txt"]


def test_discover_files_deduplicates_paths(tmp_path: Path):
    p = tmp_path / "a.csv"
    p.write_text("x\n", encoding="utf-8")
    result = discover_files([p, p])
    assert result.supported == [p.resolve()]
