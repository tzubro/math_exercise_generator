$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $pythonLauncher) {
        throw "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/windows/ and enable the Python launcher."
    }

    $pythonVersion = & py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($LASTEXITCODE -ne 0) { throw "Could not determine the installed Python version." }
    $versionParts = $pythonVersion.Trim().Split(".")
    if ([int]$versionParts[0] -lt 3 -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -lt 10)) {
        throw "Python 3.10 or newer is required; found Python $pythonVersion."
    }

    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) {
        throw "Node.js 20 or newer is required. Install it from https://nodejs.org/."
    }

    $nodeVersion = (& node --version).Trim().TrimStart("v")
    $nodeMajor = [int]$nodeVersion.Split(".")[0]
    if ($nodeMajor -lt 20) {
        throw "Node.js 20 or newer is required; found Node.js $nodeVersion."
    }

    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        & py -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Creating the Python environment failed." }
    }

    & .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Installing Python dependencies failed." }

    & $npm.Source --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw "Installing frontend dependencies failed." }

    & $npm.Source --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw "Building the frontend failed." }

    Write-Host ""
    Write-Host "Setup complete. Start the app with .\scripts\start_windows.ps1"
}
finally {
    Pop-Location
}
