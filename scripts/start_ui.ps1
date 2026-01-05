# Start Vite frontend from repo root (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Import-DotEnvIfPresent {
    param(
        [Parameter(Mandatory=$true)]
        [string]$EnvPath
    )

    if (!(Test-Path -LiteralPath $EnvPath)) {
        return
    }

    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        $line = $_
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith('#')) { return }

        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { return }

        $key = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()

        if ([string]::IsNullOrWhiteSpace($key)) { return }

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

Import-DotEnvIfPresent -EnvPath (Join-Path $repoRoot '.env')

Write-Host "=================================="
Write-Host "Starting MBSE Knowledge Graph UI"
Write-Host "=================================="
Write-Host ""

$nodeModules = Join-Path $repoRoot "node_modules"
if (!(Test-Path $nodeModules)) {
    Write-Host "Installing dependencies..."
    npm install
}

$missing = @()
foreach ($name in @('FRONTEND_HOST','FRONTEND_PORT','API_BASE_URL')) {
    if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($name))) {
        $missing += $name
    }
}
if ($missing.Count -gt 0) {
    throw "Missing required environment variables: $($missing -join ', '). Configure them in .env (see .env.example)."
}

$frontendHost = $env:FRONTEND_HOST
$frontendPort = $env:FRONTEND_PORT

if ($Detach) {
    Write-Host "Launching UI in a separate process..."
    $cmd = "Set-Location -LiteralPath '$repoRoot'; `$env:FRONTEND_HOST='$frontendHost'; `$env:FRONTEND_PORT='$frontendPort'; npm run dev -- --host $frontendHost --port $frontendPort"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $cmd
    ) | Out-Null
    exit 0
}

npm run dev -- --host $frontendHost --port $frontendPort
