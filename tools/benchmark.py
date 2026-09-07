from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import time

import psutil

from data_validator.core.config import ValidationConfig
from data_validator.core.validation_service import ValidationService


def run_benchmark(input_path: Path, output: Path) -> dict:
    process = psutil.Process(os.getpid())
    start_rss = process.memory_info().rss
    started = time.perf_counter()
    result = ValidationService().validate(
        [input_path],
        ValidationConfig(serial_regex=r"S\d+", serial_numeric_regex=r"(\d+)$"),
    )
    elapsed = time.perf_counter() - started
    end_rss = process.memory_info().rss
    data = {
        "input": str(input_path),
        "input_bytes": input_path.stat().st_size,
        "record_count": result.record_count,
        "status": result.overall_status.value,
        "elapsed_seconds": round(elapsed, 3),
        "process_rss_start_bytes": start_rss,
        "process_rss_end_bytes": end_rss,
        "cpu": platform.processor(),
        "platform": platform.platform(),
        "ram_bytes": psutil.virtual_memory().total,
        "resource_plan": result.metrics.get("resource_plan", {}),
        "rule_counts": result.metrics.get("rule_counts", {}),
        "estimated_temp_bytes": result.metrics.get("estimated_temp_bytes"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a Data Validator input dataset.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmark-result.json"))
    args = parser.parse_args()
    data = run_benchmark(args.input, args.output)
    print(json.dumps(data, indent=2))
    return 0 if data["status"] in {"PASS", "PASS WITH WARNINGS", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
