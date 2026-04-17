Set-Location $PSScriptRoot

if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = $PSScriptRoot
}

python -m src.app

