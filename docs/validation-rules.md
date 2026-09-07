# Validation Rules

## Result states
- **PASS**: no failures or warnings.
- **PASS WITH WARNINGS**: no failures, but warnings require review.
- **FAIL**: one or more validation failures.
- **CANCELLED**: operator cancelled; never equivalent to PASS.
- **INCOMPLETE**: validation could not fully complete; never equivalent to PASS.

## Default failure rules
`MISSING_SERIAL`, `MISSING_QR`, `DUPLICATE_RECORD`, `DUPLICATE_SERIAL`, `DUPLICATE_QR`, `SERIAL_QR_CONFLICT`, `QR_SERIAL_CONFLICT`, `INVALID_SERIAL_FORMAT`, `MIXED_SKU`, `UNEXPECTED_SKU`, `SERIAL_OUTSIDE_RANGE`, `RECORD_COUNT_MISMATCH`, `BATCH_QUANTITY_MISMATCH`, `EMPTY_FILE`, `CORRUPT_FILE`, and `REQUIRED_COLUMN_MISSING`.

Controlled failures also include QR control characters/line breaks, insufficient temporary disk, invalid configuration, no supported files, and internal errors.

## Default warning rules
- `SERIAL_GAP`
- `SERIAL_OUT_OF_ORDER`
- `QR_SURROUNDING_WHITESPACE`
- `SUSPICIOUS_SERIAL_CHARACTER`

## Quick vs Full
**Quick Check** limits duplicate/pair checks to each file independently and performs structural, missing-value, format, SKU and per-file quantity checks.

**Full Production Check** performs global duplicate/pair checks across all selected files and SKUs, then evaluates batch quantity, range, gap and ordering.

## Comparison rules
Serials are strings and preserve leading zeroes. Surrounding whitespace is trimmed for Serial comparison by default. QR Data is exact and case-sensitive by default and is not URL-normalised or otherwise rewritten.
