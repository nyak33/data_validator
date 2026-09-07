import pytest

from data_validator.core.config_parsing import parse_quantity_map


def test_parse_quantity_map_accepts_json_object_of_nonnegative_integers():
    assert parse_quantity_map('{"SKU01": 100, "SKU02": 200}') == {"SKU01": 100, "SKU02": 200}


def test_parse_quantity_map_blank_means_no_rule():
    assert parse_quantity_map("   ") == {}


def test_parse_quantity_map_rejects_negative_or_noninteger_values():
    with pytest.raises(ValueError):
        parse_quantity_map('{"SKU01": -1}')
    with pytest.raises(ValueError):
        parse_quantity_map('{"SKU01": "100"}')
