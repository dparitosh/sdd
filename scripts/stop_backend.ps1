# Stop FastAPI backend (Windows PowerShell)
# Kills the process listening on port 5000.

$ErrorActionPreference = 'SilentlyContinue'

function Get-ListeningPids([int]$Port) {
    $pids = @()

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $connections) {
            if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
                $pids += [int]$c.OwningProcess
            }
        }
        return $pids | Select-Object -Unique
    }

    # Fallback for older environments: netstat parsing
    $lines = netstat -ano | Select-String -Pattern (":$Port\s+")
    foreach ($line in $lines) {
        $parts = ($line -replace "\s+", " ").Trim().Split(' ')
        if ($parts.Length -ge 5) {
            $pid = $parts[-1]
            if ($pid -match '^\d+$' -and [int]$pid -gt 0) {
                $pids += [int]$pid
            }
        }
    }
    return $pids | Select-Object -Unique
}

$pids = Get-ListeningPids -Port 5000
if (-not $pids -or $pids.Count -eq 0) {
    Write-Host "Backend not running on port 5000."
    exit 0
}

$stoppedAny = $false
foreach ($pid in $pids) {
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Write-Host "Stopped backend process PID=$pid (port 5000)."
        $stoppedAny = $true
    } catch {
        Write-Host "Failed to stop backend PID=$pid (port 5000): $($_.Exception.Message)"
    }
}

if ($stoppedAny) {
    exit 0
}

exit 1
