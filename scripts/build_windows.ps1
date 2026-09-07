$ErrorActionPreference = "Stop"
python -m pip install --upgrade pip
python -m pip install ".[dev]"
pytest -q
ruff check src tests tools
python -m PyInstaller --noconfirm --clean DataValidator.spec
& .\dist\DataValidator\DataValidator.exe --self-test
if ($LASTEXITCODE -ne 0) { throw "Packaged self-test failed with exit code $LASTEXITCODE" }
Compress-Archive -Path .\dist\DataValidator\* -DestinationPath .\dist\DataValidator-Windows-x64.zip -Force
Write-Host "Built dist/DataValidator-Windows-x64.zip"
