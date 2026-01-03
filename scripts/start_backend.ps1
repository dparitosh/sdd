# Start FastAPI backend with correct PYTHONPATH (Windows PowerShell)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"

Set-Location $backendDir
$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    $python = "python"
}

& $python -m uvicorn src.web.app_fastapi:app --host 127.0.0.1 --port 5000 --reload
