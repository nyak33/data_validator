# Product Requirements Document — Data Validator

**Status:** Source of Truth
**Version:** 1.0
**Product:** Data Validator
**Deployment:** Offline Windows desktop application
**Target scale:** Up to approximately 260,000,000 records in a complete validation run

## 1. Objective
Build an offline Windows application that allows independent teams to run the same deterministic validation rules against large production datasets containing SKU, Serial Number, and QR Data before operational use.

The application answers one question: **Is this dataset safe to proceed based on the configured validation rules?**

## 2. Success criteria
- Non-technical users can run it without Python, Docker, command line, or database knowledge.
- Handles very large datasets using disk-backed processing.
- Detects duplicate Serial and QR values within and across selected files.
- Detects one-to-one Serial/QR integrity violations.
- Reports exact source locations for issues where practical.
- Never modifies source files.
- Works with the network disconnected.
- Produces consistent PASS / PASS WITH WARNINGS / FAIL results.

## 3. Non-goals for V1
- Serial generation
- QR generation
- Source-data correction
- Cloud upload
- Web dashboard
- User accounts
- Central shared database
- Printing control
- Physical QR scanning
- SHA-256 checksums
- Historical master registry
- Automatic file transfer

## 4. Platform and stack
Target Windows 10/11 x64.

Recommended implementation:
- Python
- DuckDB
- PySide6 / Qt
- pytest
- PyInstaller

The core validation engine must be independent from the GUI.

## 5. Input methods
Support:
1. Select Folder
2. Select Multiple Files
3. Drag and Drop

Supported formats:
- CSV
- XLSX

Default folder behaviour: scan supported files directly inside the selected folder; do not recurse into subfolders by default.

## 6. Logical fields
Minimum logical fields:
- SKU
- Serial Number
- QR Data

Column names must be mapped transparently rather than permanently hard-coded.

## 7. Source-data protection
The application must only READ, VALIDATE, and REPORT.

It must never overwrite, rename, move, delete, reorder, or automatically correct source files.

## 8. Serial handling
Serial values are identifiers and must be treated as strings.

Requirements:
- preserve leading zeros
- preserve raw value
- allow surrounding-whitespace trimming for comparison
- do not alter internal characters
- do not guess corrections
- configurable format rules

Configurable Serial rules should support:
- prefix
- year/prefix section
- alphabet section
- numeric running section
- total length
- allowed characters
- case sensitivity
- numeric running-part extraction

## 9. QR handling
QR Data is the raw payload string.

Default comparison is exact and case-sensitive.

Do not automatically lowercase, uppercase, URL-decode, URL-encode, remove query strings, alter slashes, or change punctuation.

Detect obvious structural issues such as missing values, whitespace-only values, line breaks, and control characters.

## 10. Required validation rules
### FAIL by default
- MISSING_SERIAL
- MISSING_QR
- DUPLICATE_RECORD
- DUPLICATE_SERIAL
- DUPLICATE_QR
- SERIAL_QR_CONFLICT
- QR_SERIAL_CONFLICT
- INVALID_SERIAL_FORMAT
- MIXED_SKU
- UNEXPECTED_SKU
- SERIAL_OUTSIDE_RANGE
- RECORD_COUNT_MISMATCH
- BATCH_QUANTITY_MISMATCH
- EMPTY_FILE
- CORRUPT_FILE
- REQUIRED_COLUMN_MISSING

### WARNING by default
- SERIAL_GAP
- SERIAL_OUT_OF_ORDER
- QR_SURROUNDING_WHITESPACE
- SUSPICIOUS_SERIAL_CHARACTER
- FILENAME_CONVENTION

Configurable rule severities should be supported where appropriate.

## 11. Duplicate logic
Duplicate detection must be exact and operate at both levels:
- per file
- across all files selected in the current validation batch

Classify:
- same Serial + same QR repeated => DUPLICATE_RECORD
- same Serial + different QR => DUPLICATE_SERIAL and SERIAL_QR_CONFLICT
- different Serial + same QR => DUPLICATE_QR and QR_SERIAL_CONFLICT

Serial and QR uniqueness checks must work across SKUs within the selected batch.

## 12. Serial/QR cardinality
Fundamental rule:
- one Serial maps to exactly one QR
- one QR maps to exactly one Serial

Any violation is FAIL.

## 13. SKU checks
Support:
- expected SKU
- one-SKU-per-file validation when enabled
- multiple SKUs in one overall validation run
- cross-SKU Serial duplicate checking
- cross-SKU QR duplicate checking

Do not infer SKU solely from filename unless configured.

## 14. Quantity checks
Support optional:
- expected rows per file
- expected total batch quantity
- expected quantity per SKU

Do not hard-code a maximum row count per file in V1.

## 15. Range checks
Support optional Start Serial and End Serial.

Any Serial outside an explicitly configured range is FAIL.

Numeric running-range validation must use the configured running component rather than naïve lexical comparison.

## 16. Sequence and gap checks
Serial gaps are WARNING by default.

Optimise by using numeric running portions, MIN, MAX, and distinct counts before detailed missing-value discovery.

Serial out-of-order is a separate WARNING and must not be confused with a gap.

## 17. Validation modes
### Quick Check
- readability
- headers/columns
- missing values
- Serial basic format
- SKU consistency
- row count
- per-file Serial duplicate
- per-file QR duplicate
- per-file Serial/QR integrity

### Full Production Check
Includes Quick Check plus:
- global Serial duplicate
- global QR duplicate
- cross-file conflicts
- global Serial/QR checks
- batch quantity
- range
- gap
- ordering
- cross-SKU checking

## 18. Result states
- PASS — no violations
- PASS WITH WARNINGS — warnings exist, human review required
- FAIL — at least one failure; must not proceed automatically
- CANCELLED — user cancelled; never equivalent to PASS
- INCOMPLETE — processing error prevented a complete validation; never equivalent to PASS

## 19. Performance architecture
Design for approximately 260,000,000 records.

Do not:
- load the full production dataset into Pandas
- keep unbounded Python dictionaries/sets for all records when memory becomes excessive
- repeatedly reread source files for every rule
- materialise all PASS rows
- load millions of issues into the GUI at once

Preferred flow:

Source files -> structural inspection -> controlled ingestion -> temporary DuckDB database -> set-based validation -> issue extraction -> report

Use local temporary disk for larger-than-memory processing.

## 20. Resource management
The application should detect available RAM, CPU, and temporary disk capacity.

Provide configurable DuckDB memory limit, thread count, and temp directory with sensible automatic defaults.

Target roughly 50–60% available RAM initially, but benchmark before treating this as final.

## 21. Disk safety
Before very large validation runs, estimate temporary storage where practical.

Insufficient disk must result in a controlled failure, never PASS.

## 22. Cancellation and crash safety
Long-running validation must be cancellable.

Cancellation or internal failure must:
- leave source files untouched
- never produce PASS
- clean temporary resources where safe
- preserve useful diagnostic logs

## 23. Progress UI
Show meaningful stages and available metrics:
- files processed / total
- current file
- records processed
- elapsed time
- current validation stage
- progress percentage when determinable

## 24. Result UI
Show at minimum:
- validation mode
- batch ID
- file count
- total records
- Serial duplicate count
- QR duplicate count
- Serial/QR conflict count
- missing Serial count
- missing QR count
- invalid Serial count
- gap count
- warning count
- failure count
- overall status

Do not rely on colour alone to communicate status.

## 25. Error details
Each issue should retain enough origin data to identify the problem:
- source file
- source sheet for XLSX
- source row
- SKU
- raw Serial
- raw QR where appropriate
- related file/row for duplicate relationships

Use pagination or bounded previews for very large issue sets.

## 26. Reporting
Export:
- human-readable summary text
- summary CSV
- detailed issues CSV

Reports should include:
- date/time
- application version
- validation-rule version
- validation mode
- batch ID
- file count
- record count
- overall result
- failure counts
- warning counts

Do not create a full PASS-row export.

## 27. Logging
Keep local technical logs for troubleshooting.

Log stage timing and failures, but do not unnecessarily copy full production Serial/QR datasets into logs.

## 28. Privacy and network behaviour
The application must have:
- no telemetry
- no analytics SDK
- no cloud calls
- no automatic uploads
- no external API dependency
- no network requirement

It must operate correctly while fully offline.

## 29. Versioning
Expose application version and validation-rule version in the UI and reports.

Initial rule version: `DV-V1.0`.

## 30. Benchmark requirements
Create deterministic synthetic data and benchmark progressively:
- 1M rows
- 10M rows
- 50M rows
- 100M rows
- 260M rows

Record where measurable:
- input rows
- file size
- QR average length
- CPU
- RAM
- storage type
- peak RAM
- peak temporary disk
- ingestion time
- Serial duplicate-check time
- QR duplicate-check time
- pair-check time
- total runtime

Do not invent benchmark numbers.

## 31. Required testing
At minimum verify:
- clean dataset => PASS
- missing Serial => FAIL
- missing QR => FAIL
- duplicate record => FAIL
- duplicate Serial within file => FAIL
- duplicate Serial across files => FAIL
- duplicate Serial across SKUs => FAIL
- duplicate QR within file => FAIL
- duplicate QR across files => FAIL
- Serial with two QR values => FAIL
- QR shared by two Serials => FAIL
- mixed SKU when enabled => FAIL
- unexpected SKU => FAIL
- invalid Serial format => FAIL
- outside range => FAIL
- row-count mismatch => FAIL
- batch-count mismatch => FAIL
- Serial gap => PASS WITH WARNINGS by default
- Serial out of order => PASS WITH WARNINGS by default
- empty selected file => FAIL
- corrupt selected file => never PASS
- cancellation => CANCELLED
- insufficient temp disk => controlled failure
- Unicode handling => correct
- leading-zero preservation => correct
- QR case sensitivity => exact
- source files unchanged => correct

## 32. Packaging
Deliver a reproducible portable Windows build.

End users must not need Python or Docker.

Use Windows CI to build and smoke-test the packaged application when local Windows verification is unavailable.

## 33. Documentation
Maintain:
- README.md
- docs/PRD.md
- docs/architecture.md
- docs/validation-rules.md
- docs/user-guide.md
- docs/benchmark-results.md
- PROJECT_STATUS.md

## 34. Definition of done
### Feature Complete
All required functionality exists and automated functional tests pass.

### Production Candidate
Feature Complete plus Windows packaging, integration tests, and meaningful large-scale benchmark evidence.

### Production Ready
Production Candidate plus full agreed-scale validation on suitable hardware and operational acceptance using real production-format data.

Never claim a higher status without evidence.

## 35. Locked V1 decisions
- offline desktop application
- Windows target
- Python backend
- DuckDB core engine
- PySide6 GUI
- portable Windows distribution
- no Docker requirement
- folder input
- multiple-file input
- drag/drop input
- CSV support
- XLSX support
- no default subfolder recursion
- cross-file Serial checking mandatory
- cross-file QR checking mandatory
- one-to-one Serial/QR integrity mandatory
- source-data modification prohibited
- SHA-256 held for later
- no cloud dependency
- historical master registry later

## 36. Configurable / unresolved values
These must remain configuration rather than assumptions:
- final Serial pattern
- Serial length
- prefix rules
- case-sensitivity rule
- alphabet rollover rule
- official starting value
- QR payload pattern
- QR expected length
- QR allowed characters
- exact required headers
- rows per file
- filename convention
- quantity per SKU
- gap acceptance policy

## 37. Product priority
Correctness > data safety > scalability > usability > visual polish.

A false PASS is more dangerous than a slower validation.
