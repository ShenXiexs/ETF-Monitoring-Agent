Set-Location $PSScriptRoot

if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = $PSScriptRoot
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    & $venvPython -m src.app
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m src.app
} else {
    python -m src.app
}
