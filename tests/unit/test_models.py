from data_validator.core.models import OverallStatus, Severity, ValidationIssue, ValidationResult


def test_result_status_fail_beats_warning():
    result = ValidationResult()
    result.add_issue(ValidationIssue(code="SERIAL_GAP", severity=Severity.WARNING, message="gap"))
    result.add_issue(ValidationIssue(code="MISSING_SERIAL", severity=Severity.FAIL, message="missing"))
    assert result.overall_status is OverallStatus.FAIL


def test_result_status_warning_when_no_failures():
    result = ValidationResult()
    result.add_issue(ValidationIssue(code="SERIAL_GAP", severity=Severity.WARNING, message="gap"))
    assert result.overall_status is OverallStatus.PASS_WITH_WARNINGS


def test_incomplete_state_overrides_issue_status():
    result = ValidationResult(incomplete=True)
    assert result.overall_status is OverallStatus.INCOMPLETE
