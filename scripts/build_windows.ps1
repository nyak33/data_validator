$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip
python -m pip install ".[dev]"
pytest -q
ruff check src tests tools

# Build and smoke-test the desktop application.
python -m PyInstaller --noconfirm --clean DataValidator.spec
& .\dist\DataValidator\DataValidator.exe --self-test
if ($LASTEXITCODE -ne 0) {
    throw "Packaged DataValidator self-test failed with exit code $LASTEXITCODE"
}

# Build the standalone large-scale synthetic dataset generator.
python -m PyInstaller --noconfirm --clean --onefile --name GenerateScaleDataset tools\generate_scale_dataset.py
$scaleSmoke = Join-Path $env:TEMP ("data-validator-scale-smoke-" + [guid]::NewGuid().ToString("N"))
try {
    & .\dist\GenerateScaleDataset.exe $scaleSmoke --rows 20 --rows-per-file 7 --sku-count 3
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged scale generator smoke-test failed with exit code $LASTEXITCODE"
    }
    $manifest = Get-Content (Join-Path $scaleSmoke "manifest.json") -Raw | ConvertFrom-Json
    if ($manifest.total_rows -ne 20 -or $manifest.file_count -ne 3) {
        throw "Packaged scale generator produced an unexpected manifest"
    }
}
finally {
    Remove-Item $scaleSmoke -Recurse -Force -ErrorAction SilentlyContinue
}

# Include benchmark utilities in the portable Windows folder.
New-Item -ItemType Directory -Path .\dist\DataValidator\Tools -Force | Out-Null
Copy-Item .\dist\GenerateScaleDataset.exe .\dist\DataValidator\Tools\GenerateScaleDataset.exe -Force
Copy-Item .\scripts\Generate260MTestData.bat .\dist\DataValidator\Generate260MTestData.bat -Force

Compress-Archive -Path .\dist\DataValidator\* -DestinationPath .\dist\DataValidator-Windows-x64.zip -Force
Write-Host "Built dist/DataValidator-Windows-x64.zip"
