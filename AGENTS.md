# Agent Instructions

Build this repository into a finished offline Windows desktop data validator. Treat `docs/PRD.md` as the product source of truth.

## Goal
Deliver a production-candidate application that validates very large serial-number and QR datasets using exact deterministic rules, without modifying source data.

## Core constraints
- Windows 10/11 x64 target.
- Offline operation; no telemetry, cloud dependency, external API, or hidden network requirement.
- End users must not need Python, Docker, Node.js, or a database server.
- Preferred stack: Python + DuckDB + PySide6 + pytest + PyInstaller.
- Source files are read-only inputs. Never overwrite, rename, move, delete, reorder, or auto-correct them.
- Final duplicate decisions must be exact, not probabilistic.
- Design for approximately 260,000,000 records using disk-backed processing; do not load the whole dataset into RAM.
- CSV is the primary mass-data path; XLSX must also be supported.
- Keep business rules configurable where the PRD marks them configurable.
- SHA-256 and historical master-registry features are out of scope for V1.

## Required execution discipline
1. Read `docs/PRD.md` completely before implementation.
2. Maintain `PROJECT_STATUS.md` with Done / In Progress / Blocked / Next.
3. Use test-driven development for validation logic.
4. Build the core validation engine before UI polish.
5. Benchmark progressively with deterministic synthetic data.
6. Add a Windows GitHub Actions build and smoke-test workflow.
7. Do not claim production readiness without evidence from tests, packaging, and large-scale benchmarks.
8. If a business value is unresolved but can be configuration, implement it as configuration instead of blocking.
9. Ask only when a missing rule materially affects validation correctness or architecture.

## Priority
Correctness > data safety > scalability > usability > visual polish.

A false PASS is more dangerous than a slower validation. Fail safely and report clearly.
