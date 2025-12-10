###############################################################################
# MBSE Knowledge Graph - Service Management Script (Windows PowerShell)
# Purpose: Start, stop, restart, and monitor services
# Usage: .\service_manager.ps1 [start|stop|restart|status|logs]
###############################################################################

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'backend', 'frontend', 'help')]
    [string]$Command = 'help',
    
    [Parameter(Position=1)]
    [ValidateSet('start', 'stop', 'restart')]
    [string]$SubCommand
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$PidDir = "$env:TEMP\mbse-pids"

if (-not (Test-Path $PidDir)) {
    New-Item -ItemType Directory -Path $PidDir -Force | Out-Null
}

function Show-Usage {
    Write-Host "Usage: .\service_manager.ps1 [COMMAND]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start      Start backend and frontend services"
    Write-Host "  stop       Stop all services"
    Write-Host "  restart    Restart all services"
    Write-Host "  status     Show service status"
    Write-Host "  logs       View service logs"
    Write-Host "  backend    Manage backend only (use with start/stop/restart)"
    Write-Host "  frontend   Manage frontend only (use with start/stop/restart)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\service_manager.ps1 start          # Start all services"
    Write-Host "  .\service_manager.ps1 backend start  # Start backend only"
    Write-Host "  .\service_manager.ps1 status         # Check status"
}

function Start-Backend {
    Write-Host "Starting backend..." -ForegroundColor Blue
    Set-Location $ProjectRoot
    $env:PYTHONPATH = $ProjectRoot
    
    $process = Start-Process -FilePath "python" -ArgumentList "-m", "src.web.app" `
        -RedirectStandardOutput "$env:TEMP\mbse-backend.log" `
        -RedirectStandardError "$env:TEMP\mbse-backend-error.log" `
        -PassThru -WindowStyle Hidden
    
    Start-Sleep -Seconds 2
    
    if ($process -and !$process.HasExited) {
        $process.Id | Out-File -FilePath "$PidDir\backend.pid" -Encoding ASCII
        Write-Host "[SUCCESS] Backend started (PID: $($process.Id))" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to start backend" -ForegroundColor Red
    }
}

function Stop-Backend {
    Write-Host "Stopping backend..." -ForegroundColor Blue
    
    if (Test-Path "$PidDir\backend.pid") {
        $pid = Get-Content "$PidDir\backend.pid"
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Remove-Item "$PidDir\backend.pid" -ErrorAction SilentlyContinue
            Write-Host "[SUCCESS] Backend stopped" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Backend process not found" -ForegroundColor Yellow
        }
    } else {
        Get-Process -Name python -ErrorAction SilentlyContinue | 
            Where-Object { $_.CommandLine -like "*src.web.app*" } | 
            Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "[SUCCESS] Backend stopped" -ForegroundColor Green
    }
}

function Start-Frontend {
    Write-Host "Starting frontend..." -ForegroundColor Blue
    Set-Location $ProjectRoot
    
    $process = Start-Process -FilePath "npm" -ArgumentList "run", "preview", "--", "--host", "0.0.0.0", "--port", "3001" `
        -RedirectStandardOutput "$env:TEMP\mbse-frontend.log" `
        -RedirectStandardError "$env:TEMP\mbse-frontend-error.log" `
        -PassThru -WindowStyle Hidden
    
    Start-Sleep -Seconds 2
    
    if ($process -and !$process.HasExited) {
        $process.Id | Out-File -FilePath "$PidDir\frontend.pid" -Encoding ASCII
        Write-Host "[SUCCESS] Frontend started (PID: $($process.Id))" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to start frontend" -ForegroundColor Red
    }
}

function Stop-Frontend {
    Write-Host "Stopping frontend..." -ForegroundColor Blue
    
    if (Test-Path "$PidDir\frontend.pid") {
        $pid = Get-Content "$PidDir\frontend.pid"
        try {
            # Stop the process and all child processes
            Get-Process -Id $pid -ErrorAction Stop | Stop-Process -Force
            Get-Process | Where-Object { $_.Parent.Id -eq $pid } | Stop-Process -Force -ErrorAction SilentlyContinue
            Remove-Item "$PidDir\frontend.pid" -ErrorAction SilentlyContinue
            Write-Host "[SUCCESS] Frontend stopped" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Frontend process not found" -ForegroundColor Yellow
        }
    } else {
        Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "[SUCCESS] Frontend stopped" -ForegroundColor Green
    }
}

function Show-Status {
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Backend Service:" -ForegroundColor Yellow
    if (Test-Path "$PidDir\backend.pid") {
        $pid = Get-Content "$PidDir\backend.pid"
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "[RUNNING] Backend running with PID: $pid" -ForegroundColor Green
        } else {
            Write-Host "[STOPPED] Backend not running" -ForegroundColor Red
            Remove-Item "$PidDir\backend.pid" -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "[STOPPED] Backend not running" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Frontend Service:" -ForegroundColor Yellow
    if (Test-Path "$PidDir\frontend.pid") {
        $pid = Get-Content "$PidDir\frontend.pid"
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "[RUNNING] Frontend running with PID: $pid" -ForegroundColor Green
        } else {
            Write-Host "[STOPPED] Frontend not running" -ForegroundColor Red
            Remove-Item "$PidDir\frontend.pid" -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "[STOPPED] Frontend not running" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Process details:" -ForegroundColor Yellow
    Get-Process -Name python, node -ErrorAction SilentlyContinue | 
        Select-Object Id, ProcessName, CPU, WorkingSet | 
        Format-Table -AutoSize
}

function Show-Logs {
    Write-Host "=== Service Logs ===" -ForegroundColor Cyan
    Write-Host ""
    
    if (Test-Path "$env:TEMP\mbse-backend.log") {
        Write-Host "--- Backend Log (last 20 lines) ---" -ForegroundColor Yellow
        Get-Content "$env:TEMP\mbse-backend.log" -Tail 20
        Write-Host ""
    }
    
    if (Test-Path "$env:TEMP\mbse-frontend.log") {
        Write-Host "--- Frontend Log (last 20 lines) ---" -ForegroundColor Yellow
        Get-Content "$env:TEMP\mbse-frontend.log" -Tail 20
        Write-Host ""
    }
    
    if (-not (Test-Path "$env:TEMP\mbse-backend.log") -and -not (Test-Path "$env:TEMP\mbse-frontend.log")) {
        Write-Host "No log files found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Tip: Use 'Get-Content <logfile> -Wait' to tail logs in real-time" -ForegroundColor Cyan
}

# Main script logic
switch ($Command) {
    'start' {
        Write-Host "Starting MBSE Knowledge Graph services..." -ForegroundColor Blue
        Start-Backend
        Start-Sleep -Seconds 2
        Start-Frontend
        Write-Host ""
        Write-Host "[SUCCESS] Services started. Check status with: .\service_manager.ps1 status" -ForegroundColor Green
    }
    
    'stop' {
        Write-Host "Stopping MBSE Knowledge Graph services..." -ForegroundColor Blue
        Stop-Frontend
        Stop-Backend
        Write-Host ""
        Write-Host "[SUCCESS] Services stopped" -ForegroundColor Green
    }
    
    'restart' {
        Write-Host "Restarting MBSE Knowledge Graph services..." -ForegroundColor Blue
        Stop-Frontend
        Stop-Backend
        Start-Sleep -Seconds 2
        Start-Backend
        Start-Sleep -Seconds 2
        Start-Frontend
        Write-Host ""
        Write-Host "[SUCCESS] Services restarted" -ForegroundColor Green
    }
    
    'status' {
        Show-Status
    }
    
    'logs' {
        Show-Logs
    }
    
    'backend' {
        if ($SubCommand) {
            switch ($SubCommand) {
                'start' { Start-Backend }
                'stop' { Stop-Backend }
                'restart' {
                    Stop-Backend
                    Start-Sleep -Seconds 2
                    Start-Backend
                }
            }
        } else {
            Write-Host "Usage: .\service_manager.ps1 backend [start|stop|restart]" -ForegroundColor Yellow
        }
    }
    
    'frontend' {
        if ($SubCommand) {
            switch ($SubCommand) {
                'start' { Start-Frontend }
                'stop' { Stop-Frontend }
                'restart' {
                    Stop-Frontend
                    Start-Sleep -Seconds 2
                    Start-Frontend
                }
            }
        } else {
            Write-Host "Usage: .\service_manager.ps1 frontend [start|stop|restart]" -ForegroundColor Yellow
        }
    }
    
    'help' {
        Show-Usage
    }
}
