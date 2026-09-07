# User Guide

## Run the portable Windows build
1. Download `DataValidator-Windows-x64.zip` from the approved GitHub build artifact.
2. Extract the ZIP to a local folder.
3. Double-click `DataValidator.exe`.
4. Python, Docker and a database server are not required.

## Select data
Use **Select Folder**, **Select Files**, or drag CSV/XLSX files onto the window. Folder selection scans only files directly inside the folder; subfolders are not included automatically.

## Validation modes
- **Quick Check**: useful while preparing individual files; it does not compare different files globally.
- **Full Production Check**: use before operational release; it validates the complete selected batch globally.

## Configuration
Default logical headers are `SKU`, `Serial Number`, and `QR Data`. Change the mappings when source headers differ.

Optional rules include Serial regex, running-number regex, expected SKU, expected rows per file, expected batch quantity, Start/End Serial, and one-SKU-per-file enforcement. A Serial range requires a running-number regex such as `(\d+)$` for trailing digits.

## Result
- **PASS**: enabled rules passed.
- **PASS WITH WARNINGS**: review warnings before proceeding.
- **FAIL**: one or more enabled rules failed.
- **CANCELLED / INCOMPLETE**: validation was not completed and must not be treated as approval.

## Reports
Click **Export Reports** to create `Validation_Summary.txt`, `Validation_Summary.csv`, and `Validation_Issues.csv`.

## Data safety
The application reads source files but does not modify them. Correct errors in the source system, export corrected data, and validate again.
