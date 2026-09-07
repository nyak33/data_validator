from data_validator.system.resources import estimate_temp_bytes


def test_temp_estimate_scales_with_input_and_has_safety_floor():
    base = estimate_temp_bytes(0)
    larger = estimate_temp_bytes(1_000_000)
    assert base == 512 * 1024 * 1024
    assert larger > base
