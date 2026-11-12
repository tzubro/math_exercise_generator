$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $python = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "The app is not set up yet. Run .\scripts\setup_windows.ps1 first."
    }
    if (-not (Test-Path "frontend\dist\index.html")) {
        throw "The frontend build is missing. Run .\scripts\setup_windows.ps1 first."
    }

    & $python -m backend.run_app
    if ($LASTEXITCODE -ne 0) { throw "The app stopped with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
