# Start Vite frontend from repo root (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "=================================="
Write-Host "Starting MBSE Knowledge Graph UI"
Write-Host "=================================="
Write-Host ""

$nodeModules = Join-Path $repoRoot "node_modules"
if (!(Test-Path $nodeModules)) {
    Write-Host "Installing dependencies..."
    npm install
}

if ($Detach) {
    Write-Host "Launching UI in a separate process..."
    $cmd = "Set-Location -LiteralPath '$repoRoot'; npm run dev"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $cmd
    ) | Out-Null
    exit 0
}

npm run dev
