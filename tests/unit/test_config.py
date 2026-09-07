from data_validator.core.config import ColumnMapping, ValidationConfig


def test_default_qr_comparison_is_case_sensitive():
    cfg = ValidationConfig()
    assert cfg.qr_case_sensitive is True


def test_column_mapping_defaults_are_neutral():
    mapping = ColumnMapping()
    assert mapping.sku == "SKU"
    assert mapping.serial == "Serial Number"
    assert mapping.qr == "QR Data"
