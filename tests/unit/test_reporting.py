from pathlib import Path

from data_validator.core.models import Severity, ValidationIssue, ValidationResult
from data_validator.reporting.exporter import export_reports


def test_export_reports_writes_summary_and_issue_csv(tmp_path: Path):
    result = ValidationResult(batch_id="BATCH-1", file_count=2, record_count=10)
    result.add_issue(ValidationIssue(
        code="DUPLICATE_SERIAL",
        severity=Severity.FAIL,
        message="duplicate",
        source_file="a.csv",
        source_row=2,
        serial="0001",
        related_file="b.csv",
        related_row=9,
    ))
    outputs = export_reports(result, tmp_path)
    assert outputs.summary_text.exists()
    assert outputs.summary_csv.exists()
    assert outputs.issues_csv.exists()
    assert "FAIL" in outputs.summary_text.read_text(encoding="utf-8")
    issue_text = outputs.issues_csv.read_text(encoding="utf-8-sig")
    assert "DUPLICATE_SERIAL" in issue_text
    assert "a.csv" in issue_text
    assert "b.csv" in issue_text
