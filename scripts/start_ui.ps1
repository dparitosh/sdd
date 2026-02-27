# Start Vite frontend from repo root (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Test-PortListening {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port
    )

    $cmd = Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop
            return ($null -ne $c -and @($c).Count -gt 0)
        } catch {
            # fall back below
        }
    }

    try {
        $pattern = ":$Port\s+.*LISTENING"
        $m = netstat -ano 2>$null | Select-String -Pattern $pattern
        return ($null -ne $m)
    } catch {
        return $false
    }
}

function Resolve-AvailablePort {
    param(
        [Parameter(Mandatory=$true)]
        [int]$StartPort,
        [int]$MaxAttempts = 20
    )

    for ($i = 0; $i -lt $MaxAttempts; $i++) {
        $p = $StartPort + $i
        if (-not (Test-PortListening -Port $p)) {
            return $p
        }
    }
    return $StartPort
}

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

# Normalize legacy variable names (older deployment templates)
if ([string]::IsNullOrWhiteSpace($env:API_BASE_URL)) {
    if (-not [string]::IsNullOrWhiteSpace($env:VITE_API_BASE_URL)) { $env:API_BASE_URL = $env:VITE_API_BASE_URL }
    elseif (-not [string]::IsNullOrWhiteSpace($env:VITE_API_URL)) { $env:API_BASE_URL = $env:VITE_API_URL }
}
if ([string]::IsNullOrWhiteSpace($env:FRONTEND_HOST) -and -not [string]::IsNullOrWhiteSpace($env:VITE_HOST)) {
    $env:FRONTEND_HOST = $env:VITE_HOST
}
if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT) -and -not [string]::IsNullOrWhiteSpace($env:VITE_PORT)) {
    $env:FRONTEND_PORT = $env:VITE_PORT
}

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

$desiredPort = [int]$frontendPort
$availablePort = Resolve-AvailablePort -StartPort $desiredPort
if ($availablePort -ne $desiredPort) {
    Write-Host "[WARNING] Port $desiredPort is already in use; using $availablePort instead. Update FRONTEND_PORT in .env to avoid this." -ForegroundColor Yellow
    $frontendPort = $availablePort
    $env:FRONTEND_PORT = "$availablePort"
    # keep legacy name in sync
    if ([string]::IsNullOrWhiteSpace($env:VITE_PORT)) { $env:VITE_PORT = "$availablePort" }
}

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
