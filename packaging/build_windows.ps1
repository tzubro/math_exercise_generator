$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $npm = Get-Command npm.cmd -ErrorAction Stop
    $pythonLauncher = Get-Command py -ErrorAction Stop

    & $npm.Source --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw "Installing frontend dependencies failed." }

    & $npm.Source --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw "Building the frontend failed." }

    $python = Join-Path $projectRoot ".venv-packaging\Scripts\python.exe"
    if (Test-Path $python) {
        $packagingVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($LASTEXITCODE -ne 0 -or $packagingVersion.Trim() -ne "3.11") {
            Remove-Item -LiteralPath ".venv-packaging" -Recurse -Force
        }
    }

    if (-not (Test-Path $python)) {
        & $pythonLauncher.Source -3.11 -m venv .venv-packaging
        if ($LASTEXITCODE -ne 0) { throw "Creating the packaging environment failed." }
    }

    & $python -m pip install -r backend\requirements.txt -r packaging\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Installing packaging dependencies failed." }

    New-Item -ItemType Directory -Force build\pyinstaller | Out-Null
    & $python -m PyInstaller `
        --clean `
        --noconfirm `
        --onedir `
        --console `
        --name MathTestGenerator `
        --paths $projectRoot `
        --specpath build\pyinstaller `
        --workpath build\pyinstaller\work `
        --distpath dist `
        --add-data "$projectRoot\frontend\dist;frontend\dist" `
        (Join-Path $projectRoot "backend\run_app.py")
    if ($LASTEXITCODE -ne 0) { throw "Packaging the application failed." }

    Write-Host "Portable app created at dist\MathTestGenerator"
}
finally {
    Pop-Location
}
