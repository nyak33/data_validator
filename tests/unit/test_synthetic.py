from pathlib import Path

from tools.generate_synthetic_data import generate_csv


def test_synthetic_generator_is_deterministic_and_can_inject_duplicate(tmp_path: Path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    generate_csv(a, 5, duplicate_serial_at=5)
    generate_csv(b, 5, duplicate_serial_at=5)
    assert a.read_bytes() == b.read_bytes()
    text = a.read_text(encoding="utf-8")
    assert "S000000000001" in text
    assert text.count("S000000000001") == 2
