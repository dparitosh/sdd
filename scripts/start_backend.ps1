# Start FastAPI backend with correct PYTHONPATH (Windows PowerShell)

param(
    [switch]$Detach
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"

Set-Location $repoRoot
$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"

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

        # Remove surrounding quotes
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        # Don't override explicitly-set env vars
        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

Import-DotEnvIfPresent -EnvPath (Join-Path $repoRoot '.env')

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

if ($Detach) {
    Write-Host "Launching backend in a separate process..."

    $cmd = @(
        "Set-Location -LiteralPath '$repoRoot'",
        "`$env:PYTHONPATH = '$backendDir;' + `$env:PYTHONPATH",
        "& '$python' -m uvicorn src.web.app_fastapi:app --host '$backendHost' --port '$backendPort' --reload"
    ) -join '; '

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $cmd
    ) | Out-Null
    exit 0
}

& $python -m uvicorn src.web.app_fastapi:app --host $backendHost --port $backendPort --reload
