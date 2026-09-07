# Architecture

Data Validator is an offline Windows desktop application with a GUI-independent validation core.

```text
CSV / XLSX
   |
   v
Structural inspection
   |
   v
Controlled ingestion
   |
   v
Temporary local DuckDB database
   |
   +--> exact validation queries
   |
   v
ValidationResult
   |
   +--> desktop results
   +--> summary report
   +--> issues CSV
```

## Components
- `core/`: configuration, normalisation, result models and validation orchestration.
- `ingestion/`: file discovery, structural inspection and temporary DuckDB ingestion.
- `reporting/`: summary and issue export.
- `system/`: resource selection and local logging.
- `ui/`: PySide6 desktop interface; the engine does not depend on the GUI.
- `tools/`: deterministic synthetic-data generation and benchmark runner.

## Large-data strategy
The production path does not load the complete dataset into Pandas or retain every Serial/QR in Python sets. CSV data is scanned by DuckDB with columns treated as strings and stored in a temporary local database. Exact duplicate and cardinality checks are set-based SQL operations.

DuckDB receives a bounded memory target and local spill directory. The initial automatic memory target is about 55% of available RAM, with thread count constrained by memory and physical cores. These defaults must be refined through measured production-scale benchmarks.

XLSX is supported with openpyxl read-only streaming and batched insertion. CSV remains the preferred mass-production input format.

## Source safety
Inputs are read only. The application never overwrites, renames, moves or deletes selected files. Temporary database/spill files are separate and are removed after completion, cancellation or failure where safe.

## Exactness and offline operation
Final duplicate decisions are exact. Runtime code has no telemetry, analytics, cloud service, API or network dependency.
