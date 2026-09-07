# Data Validator

Offline Windows desktop application for exact validation of large Serial Number and QR datasets.

## Core capabilities
- CSV and XLSX inputs
- folder, multi-file and drag/drop workflows
- exact per-file and cross-file Serial/QR duplicate checks
- one-to-one Serial/QR integrity checks
- configurable Serial format, SKU, quantity, range and sequence checks
- PASS / PASS WITH WARNINGS / FAIL / CANCELLED / INCOMPLETE results
- summary and detailed issue reports
- disk-backed DuckDB processing for larger-than-memory workloads
- no runtime cloud, telemetry, API or Docker dependency

## Development
Requires Python 3.11+.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest -q
ruff check src tests tools
```

## Windows build

```powershell
.\scripts\build_windows.ps1
```

Output: `dist/DataValidator-Windows-x64.zip`. The extracted portable application contains `DataValidator.exe`; end users do not need Python or Docker.

## Documentation
- [Product requirements](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [Validation rules](docs/validation-rules.md)
- [User guide](docs/user-guide.md)
- [Benchmark results](docs/benchmark-results.md)

## Status
V1 is under implementation and verification. Production readiness requires successful large-scale benchmarking and operational acceptance using real production-format data.
