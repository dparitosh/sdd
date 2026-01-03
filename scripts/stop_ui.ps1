# Stop Vite frontend (Windows PowerShell)
# Kills the process listening on port 3001.

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

$pids = Get-ListeningPids -Port 3001
if (-not $pids -or $pids.Count -eq 0) {
    Write-Host "Frontend not running on port 3001."
    exit 0
}

$stoppedAny = $false
foreach ($pid in $pids) {
    try {
        # Stop-Process does not reliably kill child processes (npm/vite spawn node).
        # taskkill /T ensures the full tree is terminated.
        cmd /c "taskkill /PID $pid /T /F" | Out-Null
        Write-Host "Stopped frontend process tree PID=$pid (port 3001)."
        $stoppedAny = $true
    } catch {
        Write-Host "Failed to stop frontend PID=$pid (port 3001): $($_.Exception.Message)"
    }
}

if ($stoppedAny) {
    exit 0
}

exit 1
