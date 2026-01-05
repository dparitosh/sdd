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
$ProcessIdDir = "$env:TEMP\mbse-pids"

function Get-PythonExe {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Get-NpmExe {
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd -and $npmCmd.Source) {
        return $npmCmd.Source
    }

    # Fallback for PATH edge-cases
    return "npm"
}

if (-not (Test-Path $ProcessIdDir)) {
    New-Item -ItemType Directory -Path $ProcessIdDir -Force | Out-Null
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
    Write-Host ""
    Write-Host "Manual mode env vars (must be set in .env):"
    Write-Host "  BACKEND_HOST"
    Write-Host "  BACKEND_PORT"
    Write-Host "  FRONTEND_HOST"
    Write-Host "  FRONTEND_PORT"
    Write-Host "  API_BASE_URL"
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
            $existingBackendProcessId = [int](Get-Content $backendPidPath)
            $existingBackendProcess = Get-Process -Id $existingBackendProcessId -ErrorAction SilentlyContinue
            if ($existingBackendProcess) {
                Write-Host "[SUCCESS] Backend already running (PID: $existingBackendProcessId)" -ForegroundColor Green
                return
            }

            Remove-Item $backendPidPath -ErrorAction SilentlyContinue
        }

    if (-not (Test-Path (Join-Path $ProjectRoot ".env")) -and (Test-Path (Join-Path $ProjectRoot ".env.example"))) {
        Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env") -Force
        Write-Host "[WARNING] Created .env from .env.example; review credentials before production use" -ForegroundColor Yellow
    }
    
        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','BACKEND_HOST','BACKEND_PORT')

        $backendHost = $env:BACKEND_HOST
        $backendPort = $env:BACKEND_PORT

        $pythonExe = Get-PythonExe
        $process = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "src.web.app_fastapi:app", "--host", $backendHost, "--port", $backendPort `
            -RedirectStandardOutput "$env:TEMP\mbse-backend.log" `
            -RedirectStandardError "$env:TEMP\mbse-backend-error.log" `
            -PassThru -WindowStyle Hidden
    
        Start-Sleep -Seconds 2
    
        if ($process -and !$process.HasExited) {
            $process.Id | Out-File -FilePath "$ProcessIdDir\backend.pid" -Encoding ASCII
            Write-Host "[SUCCESS] Backend started (PID: $($process.Id))" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Failed to start backend" -ForegroundColor Red
        }
    } finally {
        Pop-Location
    }
}

function Stop-Backend {
    Write-Host "Stopping backend..." -ForegroundColor Blue
    
    if (Test-Path "$ProcessIdDir\backend.pid") {
        $processId = Get-Content "$ProcessIdDir\backend.pid"
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Remove-Item "$ProcessIdDir\backend.pid" -ErrorAction SilentlyContinue
            Write-Host "[SUCCESS] Backend stopped" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Backend process not found" -ForegroundColor Yellow
        }
    } else {
        $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
        $foundProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -like "*uvicorn*src.web.app_fastapi:app*" -and
                (
                    (Test-Path $venvPython -and $_.CommandLine -like ("*" + $venvPython + "*")) -or
                    $_.CommandLine -like "*\\MBSE_MOSSEC\\*"
                )
            }

        if ($foundProcs) {
            foreach ($m in $foundProcs) {
                Stop-Process -Id $m.ProcessId -Force -ErrorAction SilentlyContinue
            }
            Write-Host "[SUCCESS] Backend stopped" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] Backend PID file not found and no matching uvicorn process detected" -ForegroundColor Yellow
        }
    }
}

function Start-Frontend {
    Write-Host "Starting frontend..." -ForegroundColor Blue
    Push-Location $ProjectRoot
    try {
        $npmExe = Get-NpmExe

        $frontendPidPath = Join-Path $ProcessIdDir "frontend.pid"
        if (Test-Path $frontendPidPath) {
            $existingFrontendProcessId = [int](Get-Content $frontendPidPath)
            $existingFrontendProcess = Get-Process -Id $existingFrontendProcessId -ErrorAction SilentlyContinue
            if ($existingFrontendProcess) {
                Write-Host "[SUCCESS] Frontend already running (PID: $existingFrontendProcessId)" -ForegroundColor Green
                return
            }

            Remove-Item $frontendPidPath -ErrorAction SilentlyContinue
        }

        if (-not (Test-Path (Join-Path $ProjectRoot "node_modules"))) {
            Write-Host "node_modules not found; installing frontend dependencies..." -ForegroundColor Yellow
            & $npmExe install
        }
        
        Import-DotEnvIfPresent
        Assert-RequiredEnv -Names @('FRONTEND_HOST','FRONTEND_PORT','API_BASE_URL')

        $frontendHost = $env:FRONTEND_HOST
        $frontendPort = $env:FRONTEND_PORT

        $process = Start-Process -FilePath $npmExe -ArgumentList "run", "dev", "--", "--host", $frontendHost, "--port", $frontendPort `
            -RedirectStandardOutput "$env:TEMP\mbse-frontend.log" `
            -RedirectStandardError "$env:TEMP\mbse-frontend-error.log" `
            -PassThru -WindowStyle Hidden
    
        Start-Sleep -Seconds 2
    
        if ($process -and !$process.HasExited) {
            $process.Id | Out-File -FilePath "$ProcessIdDir\frontend.pid" -Encoding ASCII
            Write-Host "[SUCCESS] Frontend started (PID: $($process.Id))" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Failed to start frontend" -ForegroundColor Red
        }
    } finally {
        Pop-Location
    }
}

function Stop-Frontend {
    Write-Host "Stopping frontend..." -ForegroundColor Blue
    
    if (Test-Path "$ProcessIdDir\frontend.pid") {
        $processId = [int](Get-Content "$ProcessIdDir\frontend.pid")
        try {
            # Stop the process and all child processes
            Stop-Process -Id $processId -Force -ErrorAction Stop

            # Best-effort: stop child processes (Windows)
            Get-CimInstance Win32_Process -Filter "ParentProcessId=$processId" -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
            Remove-Item "$ProcessIdDir\frontend.pid" -ErrorAction SilentlyContinue
            Write-Host "[SUCCESS] Frontend stopped" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Frontend process not found" -ForegroundColor Yellow
        }
    } else {
        $viteBin1 = Join-Path $ProjectRoot "node_modules\vite\bin\vite.js"
        $viteBin2 = Join-Path $ProjectRoot "node_modules\vite\bin\vite.mjs"
        $foundProcs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                (
                    $_.CommandLine -like ("*" + $viteBin1 + "*") -or
                    $_.CommandLine -like ("*" + $viteBin2 + "*") -or
                    ($_.CommandLine -like "*vite*" -and $_.CommandLine -like "*\\MBSE_MOSSEC\\*")
                )
            }

        if ($foundProcs) {
            foreach ($m in $foundProcs) {
                Stop-Process -Id $m.ProcessId -Force -ErrorAction SilentlyContinue
            }
            Write-Host "[SUCCESS] Frontend stopped" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] Frontend PID file not found and no matching dev server process detected" -ForegroundColor Yellow
        }
    }
}

function Show-Status {
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Backend Service:" -ForegroundColor Yellow
    if (Test-Path "$ProcessIdDir\backend.pid") {
        $backendProcessId = [int](Get-Content "$ProcessIdDir\backend.pid")
        $process = Get-Process -Id $backendProcessId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "[RUNNING] Backend running with PID: $backendProcessId" -ForegroundColor Green
        } else {
            Write-Host "[STOPPED] Backend not running" -ForegroundColor Red
            Remove-Item "$ProcessIdDir\backend.pid" -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "[STOPPED] Backend not running" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Frontend Service:" -ForegroundColor Yellow
    if (Test-Path "$ProcessIdDir\frontend.pid") {
        $frontendProcessId = [int](Get-Content "$ProcessIdDir\frontend.pid")
        $process = Get-Process -Id $frontendProcessId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "[RUNNING] Frontend running with PID: $frontendProcessId" -ForegroundColor Green
        } else {
            Write-Host "[STOPPED] Frontend not running" -ForegroundColor Red
            Remove-Item "$ProcessIdDir\frontend.pid" -ErrorAction SilentlyContinue
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
