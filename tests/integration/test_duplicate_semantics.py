from pathlib import Path

from data_validator.core.config import ValidationConfig
from data_validator.core.models import OverallStatus
from data_validator.core.validation_service import ValidationService


def _write_csv(path: Path) -> None:
    path.write_text(
        "SKU,Serial Number,QR Data\n"
        "A,0001,Q1\n"
        "A,0001,Q1\n",
        encoding="utf-8",
    )


def test_exact_duplicate_pair_counts_as_record_serial_and_qr_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "duplicate_pair.csv"
    _write_csv(source)

    result = ValidationService().validate([source], ValidationConfig())

    assert result.overall_status is OverallStatus.FAIL
    assert result.count_code("DUPLICATE_RECORD") == 1
    assert result.count_code("DUPLICATE_SERIAL") == 1
    assert result.count_code("DUPLICATE_QR") == 1
