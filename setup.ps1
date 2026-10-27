$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed' }
Write-Host 'Run .\launch.ps1. In the app, Model setup downloads the verified 176 MB model once.'
