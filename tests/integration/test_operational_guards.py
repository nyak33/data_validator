from pathlib import Path

from data_validator.core.config import ValidationConfig
from data_validator.core.models import OverallStatus, ValidationMode
from data_validator.core.validation_service import ValidationService
from data_validator.system.resources import ResourcePlan


def write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = ["SKU,Serial Number,QR Data"] + [",".join(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_expected_quantity_per_sku_fails_on_mismatch(tmp_path: Path):
    path = tmp_path / "batch.csv"
    write_csv(path, [("A", "0001", "Q1"), ("A", "0002", "Q2"), ("B", "0003", "Q3")])
    config = ValidationConfig(
        mode=ValidationMode.FULL,
        expected_quantity_per_sku={"A": 2, "B": 2},
    )
    result = ValidationService().validate([path], config)
    assert result.overall_status is OverallStatus.FAIL
    assert result.count_code("SKU_QUANTITY_MISMATCH") == 1


def test_filename_convention_is_warning_only_when_configured(tmp_path: Path):
    path = tmp_path / "bad name.csv"
    write_csv(path, [("A", "0001", "Q1")])
    config = ValidationConfig(filename_regex=r"^[A-Z0-9_-]+\.csv$")
    result = ValidationService().validate([path], config)
    assert result.overall_status is OverallStatus.PASS_WITH_WARNINGS
    assert result.count_code("FILENAME_CONVENTION") == 1


def test_cancelled_run_can_never_pass(tmp_path: Path):
    path = tmp_path / "batch.csv"
    write_csv(path, [("A", f"{i:06d}", f"Q{i:06d}") for i in range(1, 500)])
    service = ValidationService()

    def on_progress(update: dict) -> None:
        if update.get("stage") == "Importing data" and update.get("files_processed") == 0:
            service.cancel()

    result = service.validate([path], ValidationConfig(), on_progress)
    assert result.overall_status is OverallStatus.CANCELLED


def test_insufficient_temp_disk_returns_incomplete(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "batch.csv"
    write_csv(path, [("A", "0001", "Q1")])

    def no_disk(*args, **kwargs):
        return ResourcePlan(
            available_memory_bytes=8 * 1024**3,
            memory_limit_mb=4096,
            threads=2,
            temp_directory=tmp_path,
            free_temp_bytes=0,
        )

    monkeypatch.setattr("data_validator.core.validation_service.choose_resource_plan", no_disk)
    result = ValidationService().validate([path], ValidationConfig())
    assert result.overall_status is OverallStatus.INCOMPLETE
    assert result.count_code("INSUFFICIENT_TEMP_DISK") == 1
