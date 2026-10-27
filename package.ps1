$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
## Exclude unrelated toolchain DLLs on a developer's PATH from dependency discovery.
$studioBuildPath = $env:PATH
$studioPythonBase = & .\.venv\Scripts\python.exe -c 'import sys; print(sys.base_prefix)'
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$PSScriptRoot\.venv\Scripts;$studioPythonBase"
    & .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --windowed --onedir --additional-hooks-dir hooks --name DealerStudio --add-data "studio/assets;studio/assets" --add-data "LICENSE;." --add-data "README.md;." --add-data "LICENSE_INVENTORY.md;." --add-data "THIRD_PARTY_NOTICES.md;." --add-data "licenses;licenses" launch.py
} finally {
    $env:PATH = $studioBuildPath
}
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
Copy-Item -LiteralPath "$PSScriptRoot\VERIFICATION.md" -Destination "$PSScriptRoot\dist\DealerStudio\_internal\VERIFICATION.md"
