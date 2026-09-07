# Data Validator V1 Implementation Plan

**Goal:** Deliver an offline Windows desktop validator for very large Serial/QR datasets with exact cross-file validation, clear reports, and a portable Windows build.

**Architecture:** A GUI-independent Python core uses DuckDB as a disk-backed validation engine. CSV ingestion uses DuckDB set-based scans; XLSX uses streaming openpyxl ingestion. PySide6 provides the Windows GUI, while reports, resource controls, benchmark tooling, and packaging are separate modules.

**Tech Stack:** Python 3.11+, DuckDB, PySide6, openpyxl, psutil, pytest, PyInstaller.

**Spec:** `docs/PRD.md`

## Global constraints
- Offline Windows 10/11 x64 target.
- No Docker, telemetry, cloud calls, or external API dependency.
- Source files are read-only inputs and must never be modified.
- Exact duplicate detection; no probabilistic PASS/FAIL.
- Scale architecture targets approximately 260,000,000 rows via disk-backed processing.
- CSV and XLSX inputs; no default recursive subfolder scan.
- SHA-256 and historical master registry are out of scope for V1.

## Tasks
1. Domain model and configuration — typed result/status/config models and exact normalisation.
2. File discovery and structural inspection — folder/files, CSV/XLSX, Unicode, corrupt/empty handling.
3. DuckDB ingestion engine — disk-backed temporary database, CSV direct ingestion, streamed XLSX batches.
4. Validation rules — required fields, format, duplicate/pair, SKU, quantity, range, gap and order logic.
5. Reporting/logging — summary text/CSV, detailed issues CSV and local diagnostic log.
6. Resource and benchmark tooling — deterministic synthetic generation, memory/thread defaults and disk guard.
7. PySide6 desktop UI — input selection, drag/drop, configuration, progress, cancellation, result and export.
8. Windows packaging and CI — PyInstaller, Windows smoke test and downloadable artifact.
9. Final verification — CI, progressive benchmarks, documentation and production-readiness gate.
