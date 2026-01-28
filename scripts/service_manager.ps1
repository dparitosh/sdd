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

function Get-PythonExe {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Mask-Value {
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
        Write-Host ("NEO4J_URI: " + (Mask-Value $env:NEO4J_URI)) -ForegroundColor DarkGray
        Write-Host ("NEO4J_USER: " + (Mask-Value $env:NEO4J_USER)) -ForegroundColor DarkGray
        Write-Host ("NEO4J_PASSWORD: " + (Mask-Value $env:NEO4J_PASSWORD -Secret)) -ForegroundColor DarkGray
        Write-Host ("BACKEND_HOST: " + (Mask-Value $env:BACKEND_HOST)) -ForegroundColor DarkGray
        Write-Host ("BACKEND_PORT: " + (Mask-Value $env:BACKEND_PORT)) -ForegroundColor DarkGray
    }
    if ($Target -eq 'frontend' -or $Target -eq 'all') {
        Write-Host ("FRONTEND_HOST: " + (Mask-Value $env:FRONTEND_HOST)) -ForegroundColor DarkGray
        Write-Host ("FRONTEND_PORT: " + (Mask-Value $env:FRONTEND_PORT)) -ForegroundColor DarkGray
        Write-Host ("API_BASE_URL: " + (Mask-Value $env:API_BASE_URL)) -ForegroundColor DarkGray
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

        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
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

        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','BACKEND_HOST','BACKEND_PORT')

        Show-Preflight -Target 'backend'

        $backendHost = $env:BACKEND_HOST
        $backendPort = $env:BACKEND_PORT

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

        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('FRONTEND_HOST','FRONTEND_PORT','API_BASE_URL')

        Show-Preflight -Target 'frontend'

        $frontendHost = $env:FRONTEND_HOST
        $frontendPort = $env:FRONTEND_PORT
        
        $logFile = Join-Path $env:TEMP "mbse-frontend.log"
        
        $npmCmd = "cd '$ProjectRoot'; npm run dev -- --host $frontendHost --port $frontendPort"
        if ($Interactive) {
            Write-Host "[INFO] Starting frontend in interactive mode (logs will stream here)" -ForegroundColor DarkGray
            $process = Start-Process -FilePath "powershell.exe" `
                -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $npmCmd `
                -PassThru -NoNewWindow
        } else {
            $process = Start-Process -FilePath "powershell.exe" `
                -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $npmCmd `
                -RedirectStandardOutput $logFile `
                -PassThru -WindowStyle Hidden
        }
        
        $process.Id | Out-File $frontendProcessIdPath
        Start-Sleep -Seconds 3
        
        if (-not $process.HasExited) {
            Write-Host "[OK] Frontend started (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "     URL: http://${frontendHost}:${frontendPort}" -ForegroundColor Cyan
            if (-not $Interactive) {
                Write-Host "     Logs: $logFile" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "[ERROR] Frontend failed to start. Check logs:" -ForegroundColor Red
            Write-Host "     $logFile" -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
}

function Stop-Backend {
    Write-Host "Stopping backend..." -ForegroundColor Blue
    $backendProcessIdPath = Join-Path $ProcessIdDir "backend.pid"
    
    if (Test-Path $backendProcessIdPath) {
        $procId = [int](Get-Content $backendProcessIdPath)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Remove-Item $backendProcessIdPath -ErrorAction SilentlyContinue
        Write-Host "[OK] Backend stopped" -ForegroundColor Green
    } else {
        # Try to find by port
        $netstat = netstat -ano 2>$null | Select-String ":5000.*LISTENING"
        if ($netstat) {
            $pids = $netstat | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
            foreach ($p in $pids) {
                if ($p -match '^\d+$' -and [int]$p -gt 4) {
                    Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
                }
            }
            Write-Host "[OK] Backend stopped" -ForegroundColor Green
        } else {
            Write-Host "[OK] Backend was not running" -ForegroundColor Green
        }
    }
}

function Stop-Frontend {
    Write-Host "Stopping frontend..." -ForegroundColor Blue
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
        $netstat = netstat -ano 2>$null | Select-String ":3001.*LISTENING"
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
        $netstat = netstat -ano 2>$null | Select-String ":5000.*LISTENING"
        if ($netstat) {
            Write-Host "[RUNNING] Backend (detected on port 5000)" -ForegroundColor Green
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
        $netstat = netstat -ano 2>$null | Select-String ":3001.*LISTENING"
        if ($netstat) {
            Write-Host "[RUNNING] Frontend (detected on port 3001)" -ForegroundColor Green
            $frontendRunning = $true
        }
    }
    if (-not $frontendRunning) {
        Write-Host "[STOPPED] Frontend" -ForegroundColor Red
    }
    
    Write-Host ""
    if ($backendRunning) {
        Write-Host "Backend API:  http://localhost:5000" -ForegroundColor Cyan
        Write-Host "API Docs:     http://localhost:5000/docs" -ForegroundColor Cyan
    }
    if ($frontendRunning) {
        Write-Host "Frontend UI:  http://localhost:3001" -ForegroundColor Cyan
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
