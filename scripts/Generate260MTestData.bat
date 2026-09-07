@echo off
setlocal
set "ROOT=%~dp0"
set "OUT=%ROOT%Synthetic_260M"

echo ============================================================
echo Data Validator - 260,000,000 Row Synthetic Test Dataset
echo ============================================================
echo.
echo Output folder:
echo %OUT%
echo.
echo This creates 260 CSV files with 1,000,000 rows each.
echo It includes a small number of deliberate errors so the
 echo validator can prove that it detects cross-file problems.
echo.
echo Recommended: at least 50-80 GB free disk space before running
 echo generation and the subsequent full validation.
echo.
pause

"%ROOT%Tools\GenerateScaleDataset.exe" "%OUT%" --rows 260000000 --rows-per-file 1000000 --sku-count 11
if errorlevel 1 (
    echo.
    echo Dataset generation FAILED.
    echo If the output folder already exists, remove it or rename it first.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Dataset generation complete.
echo ============================================================
echo Open DataValidator.exe, select the Synthetic_260M folder,
echo choose Full Production Check, and use the settings recorded
 echo in Synthetic_260M\manifest.json.
echo.
pause
