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
    [string]$SubCommand
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

        $backendPidPath = Join-Path $ProcessIdDir "backend.pid"
        if (Test-Path $backendPidPath) {
            $existingPid = [int](Get-Content $backendPidPath)
            $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
            if ($existingProcess) {
                Write-Host "[OK] Backend already running (PID: $existingPid)" -ForegroundColor Green
                return
            }
            Remove-Item $backendPidPath -ErrorAction SilentlyContinue
        }

        if (-not (Test-Path (Join-Path $ProjectRoot ".env")) -and (Test-Path (Join-Path $ProjectRoot ".env.example"))) {
            Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env") -Force
            Write-Host "[WARN] Created .env from .env.example; edit with your credentials" -ForegroundColor Yellow
        }

        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','BACKEND_HOST','BACKEND_PORT')

        $backendHost = $env:BACKEND_HOST
        $backendPort = $env:BACKEND_PORT

        $pythonExe = Get-PythonExe
        $logFile = Join-Path $env:TEMP "mbse-backend.log"
        $errFile = Join-Path $env:TEMP "mbse-backend-error.log"
        
        $process = Start-Process -FilePath $pythonExe `
            -ArgumentList "-m", "uvicorn", "src.web.app_fastapi:app", "--host", $backendHost, "--port", $backendPort `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError $errFile `
            -PassThru -WindowStyle Hidden
        
        $process.Id | Out-File $backendPidPath
        Start-Sleep -Seconds 2
        
        if (-not $process.HasExited) {
            Write-Host "[OK] Backend started (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "     URL: http://${backendHost}:${backendPort}" -ForegroundColor Cyan
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
        $frontendPidPath = Join-Path $ProcessIdDir "frontend.pid"
        if (Test-Path $frontendPidPath) {
            $existingPid = [int](Get-Content $frontendPidPath)
            $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
            if ($existingProcess) {
                Write-Host "[OK] Frontend already running (PID: $existingPid)" -ForegroundColor Green
                return
            }
            Remove-Item $frontendPidPath -ErrorAction SilentlyContinue
        }

        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('FRONTEND_HOST','FRONTEND_PORT','API_BASE_URL')

        $frontendHost = $env:FRONTEND_HOST
        $frontendPort = $env:FRONTEND_PORT
        
        $logFile = Join-Path $env:TEMP "mbse-frontend.log"
        
        $npmCmd = "cd '$ProjectRoot'; npm run dev -- --host $frontendHost --port $frontendPort"
        $process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $npmCmd `
            -RedirectStandardOutput $logFile `
            -PassThru -WindowStyle Hidden
        
        $process.Id | Out-File $frontendPidPath
        Start-Sleep -Seconds 3
        
        if (-not $process.HasExited) {
            Write-Host "[OK] Frontend started (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "     URL: http://${frontendHost}:${frontendPort}" -ForegroundColor Cyan
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
    $backendPidPath = Join-Path $ProcessIdDir "backend.pid"
    
    if (Test-Path $backendPidPath) {
        $pid = [int](Get-Content $backendPidPath)
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Remove-Item $backendPidPath -ErrorAction SilentlyContinue
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
    $frontendPidPath = Join-Path $ProcessIdDir "frontend.pid"
    
    if (Test-Path $frontendPidPath) {
        $pid = [int](Get-Content $frontendPidPath)
        # Kill the process tree
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$pid" -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Remove-Item $frontendPidPath -ErrorAction SilentlyContinue
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
    $backendPidPath = Join-Path $ProcessIdDir "backend.pid"
    $backendRunning = $false
    if (Test-Path $backendPidPath) {
        $pid = [int](Get-Content $backendPidPath)
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            $backendRunning = $true
            Write-Host "[RUNNING] Backend (PID: $pid)" -ForegroundColor Green
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
    $frontendPidPath = Join-Path $ProcessIdDir "frontend.pid"
    $frontendRunning = $false
    if (Test-Path $frontendPidPath) {
        $pid = [int](Get-Content $frontendPidPath)
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            $frontendRunning = $true
            Write-Host "[RUNNING] Frontend (PID: $pid)" -ForegroundColor Green
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
