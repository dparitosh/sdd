###############################################################################
# MBSE Knowledge Graph - Service Management Script (Windows PowerShell)
# Purpose: Start, stop, restart, and monitor services
# Usage: .\scripts\service_manager.ps1 [start|stop|restart|status|logs|help]
###############################################################################

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'backend', 'frontend', 'help')]
    [string]$Command = 'help',
    
    [Parameter(Position=1)]
    [ValidateSet('start', 'stop', 'restart', 'backend', 'frontend')]
    [string]$SubCommand,

    # If set, starts services without hiding output (logs stream in this console)
    [switch]$Interactive,

    # If set, prints detailed preflight info (no secrets) before starting services
    [switch]$Inspect
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName
$ProcessIdDir = "$env:TEMP\mbse-pids"

function Test-PortListening {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port
    )

    # Prefer Get-NetTCPConnection when available (Windows 8+/Server 2012+)
    $cmd = Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop
            return ($null -ne $c -and @($c).Count -gt 0)
        } catch {
            # Fall back to netstat below
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

function Set-RuntimeEnvCompatibility {
    # Frontend vars
    if ([string]::IsNullOrWhiteSpace($env:FRONTEND_HOST) -and -not [string]::IsNullOrWhiteSpace($env:VITE_HOST)) {
        $env:FRONTEND_HOST = $env:VITE_HOST
    }
    if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT) -and -not [string]::IsNullOrWhiteSpace($env:VITE_PORT)) {
        $env:FRONTEND_PORT = $env:VITE_PORT
    }

    # Backend vars (legacy deployment templates used API_HOST/API_PORT or FLASK_HOST/FLASK_PORT)
    if ([string]::IsNullOrWhiteSpace($env:BACKEND_HOST)) {
        if (-not [string]::IsNullOrWhiteSpace($env:API_HOST)) { $env:BACKEND_HOST = $env:API_HOST }
        elseif (-not [string]::IsNullOrWhiteSpace($env:FLASK_HOST)) { $env:BACKEND_HOST = $env:FLASK_HOST }
    }
    if ([string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
        if (-not [string]::IsNullOrWhiteSpace($env:API_PORT)) { $env:BACKEND_PORT = $env:API_PORT }
        elseif (-not [string]::IsNullOrWhiteSpace($env:FLASK_PORT)) { $env:BACKEND_PORT = $env:FLASK_PORT }
    }

    # API base URL (Vite proxy target)
    if ([string]::IsNullOrWhiteSpace($env:API_BASE_URL)) {
        if (-not [string]::IsNullOrWhiteSpace($env:VITE_API_BASE_URL)) { $env:API_BASE_URL = $env:VITE_API_BASE_URL }
        elseif (-not [string]::IsNullOrWhiteSpace($env:VITE_API_URL)) { $env:API_BASE_URL = $env:VITE_API_URL }
        elseif (-not [string]::IsNullOrWhiteSpace($env:BACKEND_HOST) -and -not [string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
            $env:API_BASE_URL = "http://$($env:BACKEND_HOST):$($env:BACKEND_PORT)"
        }
    }
}

function Get-PythonExe {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Get-NpmExe {
    <#
    .SYNOPSIS
        Resolve the npm executable path, ensuring it points to a valid Win32 binary.
        On Windows, Get-Command npm may return the extensionless Unix shell script
        instead of npm.cmd, which causes "not a valid Win32 application" errors
        with Start-Process. This helper tries npm.cmd first.
    #>

    # 1. Prefer npm.cmd next to node.exe (standard Node.js installer layout)
    $nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
    if ($nodeExe) {
        $nodeDir = Split-Path $nodeExe -Parent
        $npmCmd = Join-Path $nodeDir "npm.cmd"
        if (Test-Path -LiteralPath $npmCmd) {
            return $npmCmd
        }
    }

    # 2. Ask Get-Command but filter to .cmd / .exe only
    $candidates = Get-Command npm -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -match '\.(cmd|exe)$' } |
        Select-Object -First 1
    if ($candidates) {
        return $candidates.Source
    }

    # 3. Fallback: let PowerShell resolve at runtime (may still hit the shell-script bug)
    $fallback = (Get-Command npm -ErrorAction Stop).Source
    return $fallback
}

function Format-MaskedValue {
    param(
        [AllowNull()]
        [string]$Value,
        [switch]$Secret
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "<empty>"
    }
    if ($Secret) {
        return "<set>"
    }
    # Keep it readable but safe-ish
    if ($Value.Length -le 8) {
        return $Value
    }
    return "{0}...{1}" -f $Value.Substring(0, 4), $Value.Substring($Value.Length - 2)
}

function Show-Preflight {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('backend','frontend','all')]
        [string]$Target
    )

    if (-not $Inspect) {
        return
    }

    Write-Host "" 
    Write-Host "=== Preflight Inspection ($Target) ===" -ForegroundColor Cyan
    Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray

    try { Write-Host ("Git: " + (git --version 2>$null)) -ForegroundColor DarkGray } catch {}
    try { Write-Host ("Python: " + (python --version 2>$null)) -ForegroundColor DarkGray } catch {}
    try { Write-Host ("Node: " + (node --version 2>$null)) -ForegroundColor DarkGray } catch {}
    try { Write-Host ("npm: " + (npm --version 2>$null)) -ForegroundColor DarkGray } catch {}

    $envPath = Join-Path $ProjectRoot ".env"
    Write-Host (".env present: " + (Test-Path -LiteralPath $envPath)) -ForegroundColor DarkGray

    if ($Target -eq 'backend' -or $Target -eq 'all') {
        Write-Host ("NEO4J_URI: " + (Format-MaskedValue $env:NEO4J_URI)) -ForegroundColor DarkGray
        Write-Host ("NEO4J_USER: " + (Format-MaskedValue $env:NEO4J_USER)) -ForegroundColor DarkGray
        Write-Host ("NEO4J_PASSWORD: " + (Format-MaskedValue $env:NEO4J_PASSWORD -Secret)) -ForegroundColor DarkGray
        Write-Host ("BACKEND_HOST: " + (Format-MaskedValue $env:BACKEND_HOST)) -ForegroundColor DarkGray
        Write-Host ("BACKEND_PORT: " + (Format-MaskedValue $env:BACKEND_PORT)) -ForegroundColor DarkGray
    }
    if ($Target -eq 'frontend' -or $Target -eq 'all') {
        Write-Host ("FRONTEND_HOST: " + (Format-MaskedValue $env:FRONTEND_HOST)) -ForegroundColor DarkGray
        Write-Host ("FRONTEND_PORT: " + (Format-MaskedValue $env:FRONTEND_PORT)) -ForegroundColor DarkGray
        Write-Host ("API_BASE_URL: " + (Format-MaskedValue $env:API_BASE_URL)) -ForegroundColor DarkGray
    }
}

if (-not (Test-Path $ProcessIdDir)) {
    New-Item -ItemType Directory -Path $ProcessIdDir -Force | Out-Null
}

function Show-Usage {
    Write-Host "MBSE Knowledge Graph - Service Manager" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\scripts\service_manager.ps1 [COMMAND] [TARGET]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start       Start backend and frontend services"
    Write-Host "  stop        Stop all services"
    Write-Host "  restart     Restart all services"
    Write-Host "  status      Show service status"
    Write-Host "  logs        View service logs (use with backend/frontend)"
    Write-Host "  backend     Manage backend only (use with start/stop/restart)"
    Write-Host "  frontend    Manage frontend only (use with start/stop/restart)"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\service_manager.ps1 start           # Start all services"
    Write-Host "  .\scripts\service_manager.ps1 start -Interactive -Inspect   # Start all services with live logs + checks"
    Write-Host "  .\scripts\service_manager.ps1 stop            # Stop all services"
    Write-Host "  .\scripts\service_manager.ps1 backend start   # Start backend only"
    Write-Host "  .\scripts\service_manager.ps1 frontend stop   # Stop frontend only"
    Write-Host "  .\scripts\service_manager.ps1 status          # Check status"
    Write-Host "  .\scripts\service_manager.ps1 logs backend    # View backend logs"
    Write-Host ""
}

function Import-DotEnvIfPresent {
    param(
        # If set, values from .env overwrite any existing process env vars.
        # This makes iterative local setup predictable (edit .env -> restart -> takes effect).
        [switch]$Force
    )
    $envPath = Join-Path $ProjectRoot ".env"
    if (!(Test-Path -LiteralPath $envPath)) {
        return
    }

    Get-Content -LiteralPath $envPath | ForEach-Object {
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

        if ($Force -or [string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

function Assert-RequiredEnv {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Names
    )

    $missing = @()
    foreach ($name in $Names) {
        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($name))) {
            $missing += $name
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing required environment variables: $($missing -join ', '). Configure them in .env (see .env.example)."
    }
}

function Start-Backend {
    Write-Host "Starting backend..." -ForegroundColor Blue
    Push-Location $ProjectRoot
    try {
        $env:PYTHONPATH = Join-Path $ProjectRoot "backend"

        $backendProcessIdPath = Join-Path $ProcessIdDir "backend.pid"
        if (Test-Path $backendProcessIdPath) {
            $existingProcessId = [int](Get-Content $backendProcessIdPath)
            $existingProcess = Get-Process -Id $existingProcessId -ErrorAction SilentlyContinue
            if ($existingProcess) {
                Write-Host "[OK] Backend already running (PID: $existingProcessId)" -ForegroundColor Green
                return
            }
            Remove-Item $backendProcessIdPath -ErrorAction SilentlyContinue
        }

        if (-not (Test-Path (Join-Path $ProjectRoot ".env")) -and (Test-Path (Join-Path $ProjectRoot ".env.example"))) {
            Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env") -Force
            Write-Host "[WARN] Created .env from .env.example; edit with your credentials" -ForegroundColor Yellow
        }

        Import-DotEnvIfPresent -Force
        Set-RuntimeEnvCompatibility
        Assert-RequiredEnv -Names @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','BACKEND_HOST','BACKEND_PORT')

        Show-Preflight -Target 'backend'

        $backendHost = $env:BACKEND_HOST
        $backendPort = $env:BACKEND_PORT

        $desiredBackendPort = [int]$backendPort
        $availableBackendPort = Resolve-AvailablePort -StartPort $desiredBackendPort
        if ($availableBackendPort -ne $desiredBackendPort) {
            Write-Host "[WARN] Port $desiredBackendPort is already in use; using $availableBackendPort instead. Set BACKEND_PORT in .env to avoid this." -ForegroundColor Yellow
            $backendPort = $availableBackendPort
            $env:BACKEND_PORT = "$availableBackendPort"

            # If API_BASE_URL points at the old local port, update it for this session so the frontend proxy still works.
            if (-not [string]::IsNullOrWhiteSpace($env:API_BASE_URL)) {
                try {
                    $u = [System.Uri]$env:API_BASE_URL
                    if ($u.Port -eq $desiredBackendPort -and ($u.Host -in @('localhost','127.0.0.1','0.0.0.0') -or $u.Host -eq $backendHost)) {
                        $b = [System.UriBuilder]$u
                        $b.Port = $availableBackendPort
                        $env:API_BASE_URL = $b.Uri.AbsoluteUri.TrimEnd('/')
                        Write-Host "[INFO] Updated API_BASE_URL for this session: $($env:API_BASE_URL)" -ForegroundColor DarkGray
                    }
                } catch {
                    # ignore parse errors
                }
            }
        }

        $pythonExe = Get-PythonExe
        $logFile = Join-Path $env:TEMP "mbse-backend.log"
        $errFile = Join-Path $env:TEMP "mbse-backend-error.log"

        if ($Interactive) {
            Write-Host "[INFO] Starting backend in interactive mode (logs will stream here)" -ForegroundColor DarkGray
            $process = Start-Process -FilePath $pythonExe `
                -ArgumentList "-m", "uvicorn", "src.web.app_fastapi:app", "--host", $backendHost, "--port", $backendPort `
                -PassThru -NoNewWindow
        } else {
            $process = Start-Process -FilePath $pythonExe `
                -ArgumentList "-m", "uvicorn", "src.web.app_fastapi:app", "--host", $backendHost, "--port", $backendPort `
                -RedirectStandardOutput $logFile `
                -RedirectStandardError $errFile `
                -PassThru -WindowStyle Hidden
        }
        
        $process.Id | Out-File $backendProcessIdPath
        Start-Sleep -Seconds 2
        
        if (-not $process.HasExited) {
            Write-Host "[OK] Backend started (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "     URL: http://${backendHost}:${backendPort}" -ForegroundColor Cyan
            if (-not $Interactive) {
                Write-Host "     Logs: $logFile" -ForegroundColor DarkGray
                Write-Host "     Errors: $errFile" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "[ERROR] Backend failed to start. Check logs:" -ForegroundColor Red
            Write-Host "     $errFile" -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
}

function Start-Frontend {
    Write-Host "Starting frontend..." -ForegroundColor Blue
    Push-Location $ProjectRoot
    try {
        $frontendProcessIdPath = Join-Path $ProcessIdDir "frontend.pid"
        if (Test-Path $frontendProcessIdPath) {
            $existingProcessId = [int](Get-Content $frontendProcessIdPath)
            $existingProcess = Get-Process -Id $existingProcessId -ErrorAction SilentlyContinue
            if ($existingProcess) {
                Write-Host "[OK] Frontend already running (PID: $existingProcessId)" -ForegroundColor Green
                return
            }
            Remove-Item $frontendProcessIdPath -ErrorAction SilentlyContinue
        }

        Import-DotEnvIfPresent -Force
        Set-RuntimeEnvCompatibility
        Assert-RequiredEnv -Names @('FRONTEND_HOST','FRONTEND_PORT','API_BASE_URL')

        Show-Preflight -Target 'frontend'

        $frontendHost = $env:FRONTEND_HOST
        $frontendPort = $env:FRONTEND_PORT

        $desiredFrontendPort = [int]$frontendPort
        $availableFrontendPort = Resolve-AvailablePort -StartPort $desiredFrontendPort
        if ($availableFrontendPort -ne $desiredFrontendPort) {
            Write-Host "[WARN] Port $desiredFrontendPort is already in use; using $availableFrontendPort instead. Set FRONTEND_PORT in .env to avoid this." -ForegroundColor Yellow
            $frontendPort = $availableFrontendPort
            $env:FRONTEND_PORT = "$availableFrontendPort"
            # Keep legacy name in-sync for tools that still look for VITE_PORT.
            if ([string]::IsNullOrWhiteSpace($env:VITE_PORT)) {
                $env:VITE_PORT = "$availableFrontendPort"
            }
        }
        
        $logFile = Join-Path $env:TEMP "mbse-frontend.log"
        $errFile = Join-Path $env:TEMP "mbse-frontend-error.log"

        # Preflight: ensure the local Vite binary exists (otherwise `npm run dev` will fail with "vite not recognized")
        $viteCmd = Join-Path $ProjectRoot "node_modules\\.bin\\vite.cmd"
        if (-not (Test-Path -LiteralPath $viteCmd)) {
            Write-Host "[ERROR] Frontend dependencies are not installed (missing: $viteCmd)" -ForegroundColor Red
            Write-Host "        Run: .\\scripts\\install.ps1" -ForegroundColor Yellow
            Write-Host "        Or from repo root: npm install" -ForegroundColor Yellow
            return
        }

        # Prefer invoking npm directly with an argument list to avoid PowerShell -Command parsing and npm config warnings.
        $npmExe = Get-NpmExe
        $npmArgs = @(
            "run",
            "dev",
            "--",
            "--host",
            $frontendHost,
            "--port",
            $frontendPort
        )

        if ($Interactive) {
            Write-Host "[INFO] Starting frontend in interactive mode (logs will stream here)" -ForegroundColor DarkGray
            $process = Start-Process -FilePath $npmExe `
                -ArgumentList $npmArgs `
                -WorkingDirectory $ProjectRoot `
                -PassThru -NoNewWindow
        } else {
            $process = Start-Process -FilePath $npmExe `
                -ArgumentList $npmArgs `
                -WorkingDirectory $ProjectRoot `
                -RedirectStandardOutput $logFile `
                -RedirectStandardError $errFile `
                -PassThru -WindowStyle Hidden
        }
        
        $process.Id | Out-File $frontendProcessIdPath
        Start-Sleep -Seconds 3
        
        if (-not $process.HasExited) {
            Write-Host "[OK] Frontend started (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "     URL: http://${frontendHost}:${frontendPort}" -ForegroundColor Cyan
            if (-not $Interactive) {
                Write-Host "     Logs: $logFile" -ForegroundColor DarkGray
                Write-Host "     Errors: $errFile" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "[ERROR] Frontend failed to start. Check logs:" -ForegroundColor Red
            Write-Host "     $logFile" -ForegroundColor Yellow
            if (-not $Interactive) {
                Write-Host "     $errFile" -ForegroundColor Yellow
            }
        }
    } finally {
        Pop-Location
    }
}

function Stop-Backend {
    Write-Host "Stopping backend..." -ForegroundColor Blue
    Import-DotEnvIfPresent
    Set-RuntimeEnvCompatibility
    if ([string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
        throw "BACKEND_PORT is not set. Set it in .env (recommended) or as an environment variable."
    }
    $backendPort = [int]$env:BACKEND_PORT
    $backendProcessIdPath = Join-Path $ProcessIdDir "backend.pid"
    
    if (Test-Path $backendProcessIdPath) {
        $procId = [int](Get-Content $backendProcessIdPath)
        # Kill the process tree (uvicorn spawns worker processes)
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Remove-Item $backendProcessIdPath -ErrorAction SilentlyContinue
    } else {
        # Try to find by port
        $netstat = netstat -ano 2>$null | Select-String ":$backendPort\s+.*LISTENING"
        if ($netstat) {
            $pids = $netstat | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
            foreach ($p in $pids) {
                if ($p -match '^\d+$' -and [int]$p -gt 4) {
                    # Kill child processes first
                    Get-CimInstance Win32_Process -Filter "ParentProcessId=$p" -ErrorAction SilentlyContinue | 
                        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
                    Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }

    # Verify port is freed (up to 5 seconds)
    $freed = $false
    for ($i = 0; $i -lt 10; $i++) {
        if (-not (Test-PortListening -Port $backendPort)) {
            $freed = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if ($freed) {
        Write-Host "[OK] Backend stopped" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Backend stopped but port $backendPort may still be held by a dying process" -ForegroundColor Yellow
    }
}

function Stop-Frontend {
    Write-Host "Stopping frontend..." -ForegroundColor Blue
    Import-DotEnvIfPresent
    Set-RuntimeEnvCompatibility
    if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT)) {
        throw "FRONTEND_PORT is not set. Set it in .env (recommended) or as an environment variable."
    }
    $frontendPort = [int]$env:FRONTEND_PORT
    $frontendProcessIdPath = Join-Path $ProcessIdDir "frontend.pid"
    
    if (Test-Path $frontendProcessIdPath) {
        $procId = [int](Get-Content $frontendProcessIdPath)
        # Kill the process tree
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Remove-Item $frontendProcessIdPath -ErrorAction SilentlyContinue
        Write-Host "[OK] Frontend stopped" -ForegroundColor Green
    } else {
        # Try to find by port
        $netstat = netstat -ano 2>$null | Select-String ":$frontendPort\s+.*LISTENING"
        if ($netstat) {
            $pids = $netstat | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
            foreach ($p in $pids) {
                if ($p -match '^\d+$' -and [int]$p -gt 4) {
                    Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
                }
            }
            Write-Host "[OK] Frontend stopped" -ForegroundColor Green
        } else {
            Write-Host "[OK] Frontend was not running" -ForegroundColor Green
        }
    }
}

function Show-Status {
    Write-Host ""
    Write-Host "=== Service Status ===" -ForegroundColor Cyan

    Import-DotEnvIfPresent
    Set-RuntimeEnvCompatibility
    if ([string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
        throw "BACKEND_PORT is not set. Set it in .env (recommended) or as an environment variable."
    }
    if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT)) {
        throw "FRONTEND_PORT is not set. Set it in .env (recommended) or as an environment variable."
    }
    $backendPort = [int]$env:BACKEND_PORT
    $frontendPort = [int]$env:FRONTEND_PORT
    
    # Check backend
    $backendProcessIdPath = Join-Path $ProcessIdDir "backend.pid"
    $backendRunning = $false
    if (Test-Path $backendProcessIdPath) {
        $procId = [int](Get-Content $backendProcessIdPath)
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            $backendRunning = $true
            Write-Host "[RUNNING] Backend (PID: $procId)" -ForegroundColor Green
        }
    }
    if (-not $backendRunning) {
        $netstat = netstat -ano 2>$null | Select-String ":$backendPort\s+.*LISTENING"
        if ($netstat) {
            Write-Host "[RUNNING] Backend (detected on port $backendPort)" -ForegroundColor Green
            $backendRunning = $true
        }
    }
    if (-not $backendRunning) {
        Write-Host "[STOPPED] Backend" -ForegroundColor Red
    }
    
    # Check frontend
    $frontendProcessIdPath = Join-Path $ProcessIdDir "frontend.pid"
    $frontendRunning = $false
    if (Test-Path $frontendProcessIdPath) {
        $procId = [int](Get-Content $frontendProcessIdPath)
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            $frontendRunning = $true
            Write-Host "[RUNNING] Frontend (PID: $procId)" -ForegroundColor Green
        }
    }
    if (-not $frontendRunning) {
        $netstat = netstat -ano 2>$null | Select-String ":$frontendPort\s+.*LISTENING"
        if ($netstat) {
            Write-Host "[RUNNING] Frontend (detected on port $frontendPort)" -ForegroundColor Green
            $frontendRunning = $true
        }
    }
    if (-not $frontendRunning) {
        Write-Host "[STOPPED] Frontend" -ForegroundColor Red
    }
    
    Write-Host ""
    if ($backendRunning) {
        $backendBaseUrl = $null
        if (-not [string]::IsNullOrWhiteSpace($env:API_BASE_URL)) {
            $backendBaseUrl = $env:API_BASE_URL.TrimEnd('/')
        } elseif (-not [string]::IsNullOrWhiteSpace($env:BACKEND_HOST)) {
            $hostForDisplay = if ($env:BACKEND_HOST -eq '0.0.0.0') { 'localhost' } else { $env:BACKEND_HOST }
            $backendBaseUrl = "http://$hostForDisplay`:$backendPort"
        } else {
            $backendBaseUrl = "http://localhost`:$backendPort"
        }

        Write-Host ("Backend API:  $backendBaseUrl") -ForegroundColor Cyan
        Write-Host ("API Docs:     $backendBaseUrl/api/docs") -ForegroundColor Cyan
    }
    if ($frontendRunning) {
        $frontendBaseUrl = $null
        if (-not [string]::IsNullOrWhiteSpace($env:FRONTEND_URL)) {
            $frontendBaseUrl = $env:FRONTEND_URL.TrimEnd('/')
        } elseif (-not [string]::IsNullOrWhiteSpace($env:FRONTEND_HOST)) {
            $hostForDisplay = if ($env:FRONTEND_HOST -eq '0.0.0.0') { 'localhost' } else { $env:FRONTEND_HOST }
            $frontendBaseUrl = "http://$hostForDisplay`:$frontendPort"
        } else {
            $frontendBaseUrl = "http://localhost`:$frontendPort"
        }

        Write-Host ("Frontend UI:  $frontendBaseUrl") -ForegroundColor Cyan
    }
    Write-Host ""
}

function Show-Logs {
    param([string]$Service)
    
    if ($Service -eq 'backend') {
        $logFile = Join-Path $env:TEMP "mbse-backend.log"
        $errFile = Join-Path $env:TEMP "mbse-backend-error.log"
        Write-Host "=== Backend Logs ===" -ForegroundColor Cyan
        if (Test-Path $logFile) { Get-Content $logFile -Tail 50 }
        if (Test-Path $errFile) { 
            Write-Host "=== Backend Errors ===" -ForegroundColor Yellow
            Get-Content $errFile -Tail 20 
        }
    } elseif ($Service -eq 'frontend') {
        $logFile = Join-Path $env:TEMP "mbse-frontend.log"
        Write-Host "=== Frontend Logs ===" -ForegroundColor Cyan
        if (Test-Path $logFile) { Get-Content $logFile -Tail 50 }
    } else {
        Write-Host "Usage: .\scripts\service_manager.ps1 logs [backend|frontend]" -ForegroundColor Yellow
    }
}

# Main command handling
switch ($Command) {
    'start' {
        Start-Backend
        Start-Frontend
        Write-Host ""
        Show-Status
    }
    'stop' {
        Stop-Backend
        Stop-Frontend
    }
    'restart' {
        Stop-Backend
        Stop-Frontend
        Start-Sleep -Seconds 2
        Start-Backend
        Start-Frontend
        Show-Status
    }
    'status' {
        Show-Status
    }
    'logs' {
        Show-Logs -Service $SubCommand
    }
    'backend' {
        switch ($SubCommand) {
            'start' { Start-Backend }
            'stop' { Stop-Backend }
            'restart' { Stop-Backend; Start-Sleep -Seconds 2; Start-Backend }
            default { Write-Host "Usage: .\scripts\service_manager.ps1 backend [start|stop|restart]" -ForegroundColor Yellow }
        }
    }
    'frontend' {
        switch ($SubCommand) {
            'start' { Start-Frontend }
            'stop' { Stop-Frontend }
            'restart' { Stop-Frontend; Start-Sleep -Seconds 2; Start-Frontend }
            default { Write-Host "Usage: .\scripts\service_manager.ps1 frontend [start|stop|restart]" -ForegroundColor Yellow }
        }
    }
    'help' {
        Show-Usage
    }
    default {
        Show-Usage
    }
}
