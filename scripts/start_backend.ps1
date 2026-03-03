# Start FastAPI backend with correct PYTHONPATH (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"

Set-Location $repoRoot
$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"

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
        [string]$EnvPath,

        # If set, values from .env overwrite any existing process env vars.
        [switch]$Force
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

        # Remove surrounding quotes
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        # Default behavior keeps explicitly set env vars; -Force makes .env authoritative for this process.
        if ($Force -or [string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

Import-DotEnvIfPresent -EnvPath (Join-Path $repoRoot '.env') -Force

# Normalize legacy names (older templates used API_HOST/API_PORT or FLASK_HOST/FLASK_PORT)
if ([string]::IsNullOrWhiteSpace($env:BACKEND_HOST)) {
    if (-not [string]::IsNullOrWhiteSpace($env:API_HOST)) { $env:BACKEND_HOST = $env:API_HOST }
    elseif (-not [string]::IsNullOrWhiteSpace($env:FLASK_HOST)) { $env:BACKEND_HOST = $env:FLASK_HOST }
}
if ([string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
    if (-not [string]::IsNullOrWhiteSpace($env:API_PORT)) { $env:BACKEND_PORT = $env:API_PORT }
    elseif (-not [string]::IsNullOrWhiteSpace($env:FLASK_PORT)) { $env:BACKEND_PORT = $env:FLASK_PORT }
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    $python = "python"
}

$missing = @()
foreach ($name in @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','BACKEND_HOST','BACKEND_PORT')) {
    if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($name))) {
        $missing += $name
    }
}
if ($missing.Count -gt 0) {
    throw "Missing required environment variables: $($missing -join ', '). Configure them in .env (see .env.example)."
}

$backendHost = $env:BACKEND_HOST
$backendPort = $env:BACKEND_PORT

$desiredPort = [int]$backendPort
$availablePort = Resolve-AvailablePort -StartPort $desiredPort
if ($availablePort -ne $desiredPort) {
    Write-Host "[WARNING] Port $desiredPort is already in use; using $availablePort instead. Update BACKEND_PORT in .env to avoid this." -ForegroundColor Yellow
    $backendPort = $availablePort
    $env:BACKEND_PORT = "$availablePort"
}

if ($Detach) {
    Write-Host "Launching backend in a separate process..."

    $cmd = @(
        "Set-Location -LiteralPath '$repoRoot'",
        "`$env:PYTHONPATH = '$backendDir;' + `$env:PYTHONPATH",
        "& '$python' -m uvicorn src.web.app_fastapi:app --host '$backendHost' --port '$backendPort' --reload --reload-dir '$backendDir\src'"
    ) -join '; '

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $cmd
    ) | Out-Null
    exit 0
}

$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"
Set-Location $backendDir
& $python -m uvicorn src.web.app_fastapi:app --host $backendHost --port $backendPort --reload --reload-dir "$backendDir\src"
