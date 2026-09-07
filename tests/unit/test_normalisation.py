from data_validator.core.config import ValidationConfig
from data_validator.core.normalisation import extract_running_number, normalise_qr, normalise_serial


def test_serial_preserves_leading_zeroes_and_trims_surrounding_space():
    cfg = ValidationConfig(serial_trim_whitespace=True)
    assert normalise_serial(" 00123 ", cfg) == "00123"


def test_qr_default_is_exact_case_sensitive_except_configured_trim_key():
    cfg = ValidationConfig(qr_trim_whitespace=False)
    assert normalise_qr("AbC", cfg) == "AbC"
    assert normalise_qr("abc", cfg) == "abc"


def test_extract_running_number_uses_first_capture_group():
    cfg = ValidationConfig(serial_numeric_regex=r"(\d+)$")
    assert extract_running_number("27A00001234", cfg) == 1234
