# 260M Scale Test

This test validates the full production path using a deterministic synthetic dataset.

## Dataset layout

Default generation creates:

- 260,000,000 data rows
- 260 CSV files
- 1,000,000 rows per file
- 11 rotating SKU values (`SKU01` to `SKU11`)
- one SKU per file
- globally running Serial values in the form `S000000000001`
- globally unique QR values in the form `QR-000000000001`

The generated folder also contains `manifest.json` with the generation parameters and recommended validation settings.

## Deliberately injected issues

The default stress dataset contains a small number of known errors so validation accuracy can be checked at scale:

- 1 Serial reused with a different QR
- 1 QR reused with a different Serial
- 1 exact duplicate Serial/QR pair
- 1 missing Serial
- 1 missing QR

The duplicate locations are deliberately separated across the overall dataset so Full Production Check must perform global/cross-file checking.

## Windows portable build

The portable Windows package contains:

- `DataValidator.exe`
- `Generate260MTestData.bat`
- `Tools/GenerateScaleDataset.exe`

To create the default dataset, double-click `Generate260MTestData.bat`.

The output folder is `Synthetic_260M` beside the application.

## Recommended free disk space

Plan for at least 50–80 GB of free local SSD/NVMe space for dataset generation plus the validator's temporary DuckDB/spill files. This is a planning allowance, not a measured final requirement; actual usage must be recorded during the benchmark.

## Validation settings

Open `DataValidator.exe`, select the generated `Synthetic_260M` folder, and use **Full Production Check**.

Recommended settings for the default 260M dataset:

- Serial column: `Serial Number`
- QR column: `QR Data`
- SKU column: `SKU`
- Serial regex: `S\d{12}`
- Running-number regex: `(\d+)$`
- Expected rows/file: `1000000`
- Expected batch quantity: `260000000`
- Start Serial: `S000000000001`
- End Serial: `S000260000000`
- Require one SKU per file: enabled

The same settings are recorded in `manifest.json`.

## Expected core findings

At minimum the error-injected dataset should report:

- `DUPLICATE_SERIAL`: 1
- `SERIAL_QR_CONFLICT`: 1
- `DUPLICATE_QR`: 1
- `QR_SERIAL_CONFLICT`: 1
- `DUPLICATE_RECORD`: 1
- `MISSING_SERIAL`: 1
- `MISSING_QR`: 1

Sequence warnings can also occur because deliberate duplicate/missing Serial injections remove original running values from the otherwise continuous sequence.

## What to record

For production-scale evidence record:

- hardware CPU
- installed RAM
- drive model/type if known
- free disk before generation
- generated dataset size
- generation time
- validation start/end time
- peak RAM if measurable
- peak temporary disk usage if measurable
- final validation status
- issue counts

Do not call the 260M capability production-proven until this test completes on suitable hardware and the detected findings match the known injected dataset.
