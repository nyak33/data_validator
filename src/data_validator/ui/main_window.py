from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data_validator import RULES_VERSION, __version__
from data_validator.core.config import ColumnMapping, ValidationConfig
from data_validator.core.models import ValidationMode, ValidationResult
from data_validator.core.validation_service import ValidationService
from data_validator.ingestion.discovery import discover_files, discover_folder
from data_validator.reporting.exporter import export_reports


class ValidationWorker(QObject):
    progress = Signal(dict)
    finished = Signal(object)

    def __init__(self, files: list[Path], config: ValidationConfig):
        super().__init__()
        self.files = files
        self.config = config
        self.service = ValidationService()

    @Slot()
    def run(self) -> None:
        result = self.service.validate(self.files, self.config, self.progress.emit)
        self.finished.emit(result)

    @Slot()
    def cancel(self) -> None:
        self.service.cancel()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Data Validator {__version__}")
        self.resize(1000, 760)
        self.setAcceptDrops(True)
        self.files: list[Path] = []
        self.result: ValidationResult | None = None
        self.thread: QThread | None = None
        self.worker: ValidationWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("Data Validator")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Offline validation • App {__version__} • Rules {RULES_VERSION}"))

        input_row = QHBoxLayout()
        folder_btn = QPushButton("Select Folder")
        files_btn = QPushButton("Select Files")
        clear_btn = QPushButton("Clear")
        folder_btn.clicked.connect(self.select_folder)
        files_btn.clicked.connect(self.select_files)
        clear_btn.clicked.connect(self.clear_files)
        input_row.addWidget(folder_btn)
        input_row.addWidget(files_btn)
        input_row.addWidget(clear_btn)
        input_row.addStretch(1)
        layout.addLayout(input_row)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.file_list.setMinimumHeight(110)
        layout.addWidget(self.file_list)

        settings = QGroupBox("Validation Settings")
        form = QFormLayout(settings)
        self.mode = QComboBox()
        self.mode.addItem("Full Production Check", ValidationMode.FULL)
        self.mode.addItem("Quick Check", ValidationMode.QUICK)
        self.batch_id = QLineEdit()
        self.sku_column = QLineEdit("SKU")
        self.serial_column = QLineEdit("Serial Number")
        self.qr_column = QLineEdit("QR Data")
        self.serial_regex = QLineEdit()
        self.serial_numeric_regex = QLineEdit()
        self.expected_sku = QLineEdit()
        self.expected_rows = QLineEdit()
        self.expected_batch = QLineEdit()
        self.start_serial = QLineEdit()
        self.end_serial = QLineEdit()
        self.one_sku = QCheckBox("Require one SKU per file")
        form.addRow("Mode", self.mode)
        form.addRow("Batch ID", self.batch_id)
        form.addRow("SKU column", self.sku_column)
        form.addRow("Serial column", self.serial_column)
        form.addRow("QR column", self.qr_column)
        form.addRow("Serial regex (optional)", self.serial_regex)
        form.addRow("Running-number regex (optional)", self.serial_numeric_regex)
        form.addRow("Expected SKU (optional)", self.expected_sku)
        form.addRow("Expected rows/file (optional)", self.expected_rows)
        form.addRow("Expected batch quantity (optional)", self.expected_batch)
        form.addRow("Start Serial (optional)", self.start_serial)
        form.addRow("End Serial (optional)", self.end_serial)
        form.addRow("SKU rule", self.one_sku)
        layout.addWidget(settings)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Run Validation")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.export_btn = QPushButton("Export Reports")
        self.export_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.run_validation)
        self.cancel_btn.clicked.connect(self.cancel_validation)
        self.export_btn.clicked.connect(self.export_reports_clicked)
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.cancel_btn)
        run_row.addWidget(self.export_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)

        self.progress_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("No validation run yet.")
        status_font = self.status_label.font()
        status_font.setBold(True)
        status_font.setPointSize(14)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        self.summary_label = QLabel("")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.summary_label)

        self.issue_table = QTableWidget(0, 6)
        self.issue_table.setHorizontalHeaderLabels(["Severity", "Code", "File", "Row", "Serial", "Description"])
        self.issue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.issue_table.setAlternatingRowColors(True)
        layout.addWidget(self.issue_table, 1)
        self.setCentralWidget(root)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self._add_paths(paths)
        event.acceptProposedAction()

    @Slot()
    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Data Folder")
        if folder:
            found = discover_folder(Path(folder), recursive=False)
            self._merge_files(found.supported)
            if found.ignored:
                self.progress_label.setText(f"Ignored {len(found.ignored)} unsupported file(s).")

    @Slot()
    def select_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "Select Data Files", "", "Data files (*.csv *.xlsx)")
        if names:
            self._add_paths([Path(name) for name in names])

    def _add_paths(self, paths: list[Path]) -> None:
        files: list[Path] = []
        for path in paths:
            if path.is_dir():
                files.extend(discover_folder(path, recursive=False).supported)
            else:
                files.extend(discover_files([path]).supported)
        self._merge_files(files)

    def _merge_files(self, files: list[Path]) -> None:
        existing = {p.resolve() for p in self.files}
        for path in files:
            path = path.resolve()
            if path not in existing:
                self.files.append(path)
                existing.add(path)
        self.files.sort(key=lambda p: (p.name.lower(), str(p).lower()))
        self.file_list.clear()
        self.file_list.addItems([str(p) for p in self.files])
        self.progress_label.setText(f"{len(self.files)} supported file(s) selected.")

    @Slot()
    def clear_files(self) -> None:
        if self.thread is not None:
            return
        self.files.clear()
        self.file_list.clear()
        self.progress_label.setText("Ready")

    def _int_or_none(self, edit: QLineEdit, label: str) -> int | None:
        text = edit.text().strip()
        if not text:
            return None
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"{label} must be a whole number.") from exc
        if value < 0:
            raise ValueError(f"{label} cannot be negative.")
        return value

    def _config(self) -> ValidationConfig:
        if not self.sku_column.text().strip() or not self.serial_column.text().strip() or not self.qr_column.text().strip():
            raise ValueError("Column mappings cannot be blank.")
        return ValidationConfig(
            columns=ColumnMapping(
                sku=self.sku_column.text().strip(),
                serial=self.serial_column.text().strip(),
                qr=self.qr_column.text().strip(),
            ),
            mode=self.mode.currentData(),
            batch_id=self.batch_id.text().strip(),
            serial_regex=self.serial_regex.text().strip() or None,
            serial_numeric_regex=self.serial_numeric_regex.text().strip() or None,
            expected_sku=self.expected_sku.text().strip() or None,
            expected_rows_per_file=self._int_or_none(self.expected_rows, "Expected rows/file"),
            expected_batch_quantity=self._int_or_none(self.expected_batch, "Expected batch quantity"),
            start_serial=self.start_serial.text().strip() or None,
            end_serial=self.end_serial.text().strip() or None,
            one_sku_per_file=self.one_sku.isChecked(),
        )

    @Slot()
    def run_validation(self) -> None:
        if not self.files:
            QMessageBox.warning(self, "No files", "Select at least one CSV or XLSX file.")
            return
        try:
            config = self._config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        self.result = None
        self.export_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("Starting validation...")
        self.status_label.setText("VALIDATING")
        self.issue_table.setRowCount(0)

        self.thread = QThread(self)
        self.worker = ValidationWorker(list(self.files), config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    @Slot(dict)
    def on_progress(self, update: dict) -> None:
        stage = update.get("stage", "Working")
        done = int(update.get("files_processed", 0) or 0)
        total = int(update.get("total_files", 0) or 0)
        records = int(update.get("records_processed", 0) or 0)
        current = update.get("current_file")
        detail = f" • {Path(current).name}" if current else ""
        self.progress_label.setText(f"{stage}{detail} • {records:,} records")
        if total > 0 and stage in {"Inspecting files", "Importing data"}:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int((done / total) * 100))
        else:
            self.progress_bar.setRange(0, 0)

    @Slot(object)
    def on_finished(self, result: ValidationResult) -> None:
        self.result = result
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Completed • {result.record_count:,} records")
        self.status_label.setText(result.overall_status.value)
        counts = result.metrics.get("rule_counts", {})
        serial_dup = counts.get("DUPLICATE_SERIAL", 0)
        qr_dup = counts.get("DUPLICATE_QR", 0)
        conflicts = counts.get("SERIAL_QR_CONFLICT", 0) + counts.get("QR_SERIAL_CONFLICT", 0)
        self.summary_label.setText(
            f"Files: {result.file_count:,}   Records: {result.record_count:,}   "
            f"Failures: {result.failure_count:,}   Warnings: {result.warning_count:,}\n"
            f"Duplicate Serial: {serial_dup:,}   Duplicate QR: {qr_dup:,}   Pair conflicts: {conflicts:,}"
        )
        preview = result.issues[:1000]
        self.issue_table.setRowCount(len(preview))
        for row, issue in enumerate(preview):
            values = [
                issue.severity.value,
                issue.code,
                issue.source_file or "",
                "" if issue.source_row is None else str(issue.source_row),
                issue.serial or "",
                issue.message,
            ]
            for column, value in enumerate(values):
                self.issue_table.setItem(row, column, QTableWidgetItem(value))
        self.issue_table.resizeColumnsToContents()
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    @Slot()
    def _thread_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None
        self.run_btn.setEnabled(True)

    @Slot()
    def cancel_validation(self) -> None:
        if self.worker is not None:
            self.progress_label.setText("Cancelling...")
            self.worker.cancel()

    @Slot()
    def export_reports_clicked(self) -> None:
        if self.result is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Report Folder")
        if not folder:
            return
        output = Path(folder) / (f"Validation_{self.result.batch_id}" if self.result.batch_id else "Validation_Report")
        reports = export_reports(self.result, output)
        QMessageBox.information(self, "Reports exported", f"Reports saved to:\n{reports.summary_text.parent}")
