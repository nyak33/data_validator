from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from data_validator import RULES_VERSION, __version__
from data_validator.core.models import ValidationResult


@dataclass(slots=True)
class ReportOutputs:
    summary_text: Path
    summary_csv: Path
    issues_csv: Path


def export_reports(result: ValidationResult, output_dir: Path) -> ReportOutputs:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_text = output_dir / "Validation_Summary.txt"
    summary_csv = output_dir / "Validation_Summary.csv"
    issues_csv = output_dir / "Validation_Issues.csv"
    generated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    rule_counts = result.metrics.get("rule_counts", {})

    lines = [
        "DATA VALIDATOR — VALIDATION SUMMARY",
        "",
        f"Generated: {generated}",
        f"Application Version: {__version__}",
        f"Rules Version: {RULES_VERSION}",
        f"Mode: {result.mode.value}",
        f"Batch ID: {result.batch_id or '-'}",
        f"Files: {result.file_count:,}",
        f"Records: {result.record_count:,}",
        f"Failures: {result.failure_count:,}",
        f"Warnings: {result.warning_count:,}",
        f"Overall Result: {result.overall_status.value}",
        "",
        "Rule Counts:",
    ]
    for code, count in sorted(rule_counts.items()):
        lines.append(f"- {code}: {count:,}")
    summary_text.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with summary_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "value"])
        writer.writerow(["generated", generated])
        writer.writerow(["application_version", __version__])
        writer.writerow(["rules_version", RULES_VERSION])
        writer.writerow(["mode", result.mode.value])
        writer.writerow(["batch_id", result.batch_id])
        writer.writerow(["file_count", result.file_count])
        writer.writerow(["record_count", result.record_count])
        writer.writerow(["failure_count", result.failure_count])
        writer.writerow(["warning_count", result.warning_count])
        writer.writerow(["overall_status", result.overall_status.value])
        for code, count in sorted(rule_counts.items()):
            writer.writerow([f"rule_count.{code}", count])

    fields = [
        "severity", "issue_code", "source_file", "source_sheet", "source_row",
        "sku", "serial", "qr", "related_file", "related_row", "description", "metadata",
    ]
    with issues_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for issue in result.issues:
            writer.writerow({
                "severity": issue.severity.value,
                "issue_code": issue.code,
                "source_file": issue.source_file or "",
                "source_sheet": issue.source_sheet or "",
                "source_row": "" if issue.source_row is None else issue.source_row,
                "sku": issue.sku or "",
                "serial": issue.serial or "",
                "qr": issue.qr or "",
                "related_file": issue.related_file or "",
                "related_row": "" if issue.related_row is None else issue.related_row,
                "description": issue.message,
                "metadata": repr(issue.metadata) if issue.metadata else "",
            })

    return ReportOutputs(summary_text=summary_text, summary_csv=summary_csv, issues_csv=issues_csv)
