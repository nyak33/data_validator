from __future__ import annotations

import json


def parse_quantity_map(text: str) -> dict[str, int]:
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("SKU quantities must be valid JSON, for example {\"SKU01\": 1000}.") from exc
    if not isinstance(value, dict):
        raise ValueError("SKU quantities must be a JSON object.")

    result: dict[str, int] = {}
    for key, quantity in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Every SKU quantity key must be a non-empty string.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError(f"Quantity for {key!r} must be a non-negative whole number.")
        result[key] = quantity
    return result
