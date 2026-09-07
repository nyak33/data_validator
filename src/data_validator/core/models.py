from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    WARNING = "WARNING"
    FAIL = "FAIL"


class OverallStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS WITH WARNINGS"
    FAIL = "FAIL"
    CANCELLED = "CANCELLED"
    INCOMPLETE = "INCOMPLETE"


class ValidationMode(str, Enum):
    QUICK = "QUICK"
    FULL = "FULL"


@dataclass(slots=True)
class ValidationIssue:
    code: str
    severity: Severity
    message: str
    source_file: str | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    sku: str | None = None
    serial: str | None = None
    qr: str | None = None
    related_file: str | None = None
    related_row: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FileSummary:
    path: Path
    rows: int = 0
    file_id: int | None = None
    status: str = "READY"
    message: str = ""


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)
    file_count: int = 0
    record_count: int = 0
    batch_id: str = ""
    mode: ValidationMode = ValidationMode.FULL
    cancelled: bool = False
    incomplete: bool = False
    file_summaries: list[FileSummary] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    @property
    def failure_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.FAIL)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.WARNING)

    @property
    def overall_status(self) -> OverallStatus:
        if self.cancelled:
            return OverallStatus.CANCELLED
        if self.incomplete:
            return OverallStatus.INCOMPLETE
        if self.failure_count:
            return OverallStatus.FAIL
        if self.warning_count:
            return OverallStatus.PASS_WITH_WARNINGS
        return OverallStatus.PASS

    def count_code(self, code: str) -> int:
        return sum(1 for issue in self.issues if issue.code == code)
