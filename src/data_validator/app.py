from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from data_validator.core.config import ValidationConfig
from data_validator.core.models import OverallStatus
from data_validator.core.validation_service import ValidationService
from data_validator.system.logging_setup import configure_logging


def self_test() -> int:
    from openpyxl import Workbook

    with tempfile.TemporaryDirectory(prefix="data_validator_selftest_") as temp:
        root = Path(temp)
        csv_path = root / "sample.csv"
        csv_path.write_text("SKU,Serial Number,QR Data\nA,0001,QRA\nA,0002,QRB\n", encoding="utf-8")
        xlsx_path = root / "sample.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["SKU", "Serial Number", "QR Data"])
        ws.append(["B", "0003", "QRC"])
        wb.save(xlsx_path)
        result = ValidationService().validate([csv_path, xlsx_path], ValidationConfig())
        return 0 if result.overall_status is OverallStatus.PASS and result.record_count == 3 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--self-test", action="store_true", help="Run packaged smoke test and exit")
    args = parser.parse_args(argv)
    configure_logging()
    if args.self_test:
        return self_test()

    from PySide6.QtWidgets import QApplication
    from data_validator.ui.main_window import MainWindow

    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
