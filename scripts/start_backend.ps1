# Start FastAPI backend with correct PYTHONPATH (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"

Set-Location $backendDir
$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    $python = "python"
}

if ($Detach) {
    Write-Host "Launching backend in a separate process..."

    $cmd = @(
        "Set-Location -LiteralPath '$backendDir'",
        "`$env:PYTHONPATH = '$backendDir;' + `$env:PYTHONPATH",
        "& '$python' -m uvicorn src.web.app_fastapi:app --host 127.0.0.1 --port 5000 --reload"
    ) -join '; '

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $cmd
    ) | Out-Null
    exit 0
}

& $python -m uvicorn src.web.app_fastapi:app --host 127.0.0.1 --port 5000 --reload
