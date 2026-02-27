# Stop Vite frontend (Windows PowerShell)
# Kills the process listening on FRONTEND_PORT (from .env/environment).

# PSScriptAnalyzer -IgnoreRule PSUseApprovedVerbs

$ErrorActionPreference = 'Stop'

function Import-DotEnvIfPresent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath
    )

    if (-not (Test-Path -LiteralPath $EnvPath)) {
        return
    }

    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $parts = $line -split '=', 2
        if ($parts.Length -ne 2) { return }
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path "Env:$name" -Value $value
    }
}

# Load .env from repo root (one level above scripts/)
$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
Import-DotEnvIfPresent -EnvPath $envPath

if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT)) {
    throw "FRONTEND_PORT is not set. Set it in .env (recommended) or as an environment variable."
}
$frontendPort = [int]$env:FRONTEND_PORT

function Get-ChildProcessIds([int]$ParentPid) {
    if (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) {
        try {
            return (Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentPid" | Select-Object -ExpandProperty ProcessId)
        } catch {
            return @()
        }
    }

    try {
        return (Get-WmiObject Win32_Process -Filter "ParentProcessId=$ParentPid" | Select-Object -ExpandProperty ProcessId)
    } catch {
        return @()
    }
}

function Stop-ProcessTree([int]$RootPid) {
    if ($RootPid -le 4) {
        throw "Refusing to terminate protected PID=$RootPid"
    }

    $toVisit = New-Object System.Collections.Generic.Queue[int]
    $visited = New-Object System.Collections.Generic.HashSet[int]
    $ordered = New-Object System.Collections.Generic.List[int]

    $toVisit.Enqueue($RootPid)
    while ($toVisit.Count -gt 0) {
        $current = $toVisit.Dequeue()
        if (-not $visited.Add($current)) { continue }
        $ordered.Add($current) | Out-Null

        foreach ($child in (Get-ChildProcessIds -ParentPid $current)) {
            if ($child -and $child -gt 0) {
                $toVisit.Enqueue([int]$child)
            }
        }
    }

    # Kill children first
    for ($i = $ordered.Count - 1; $i -ge 0; $i--) {
        $pidToKill = $ordered[$i]
        if ($pidToKill -le 4) { continue }
        Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
    }
}

function Get-ListeningPids([int]$Port) {
    $pids = @()

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
            foreach ($c in $connections) {
                if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
                    $pids += [int]$c.OwningProcess
                }
            }
            $pids = $pids | Select-Object -Unique
            if ($pids -and $pids.Count -gt 0) {
                return $pids
            }
        } catch {
            # Fall back to netstat
        }
    }

    # Netstat fallback (works even when Get-NetTCPConnection returns nothing)
    $netstatLines = netstat -ano -p tcp | Select-String -Pattern "LISTENING" | ForEach-Object { $_.Line }
    foreach ($line in $netstatLines) {
        # Handles IPv4 and IPv6 formats, e.g. 0.0.0.0:3001 or [::]:3001
        if ($line -match "\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            $linePort = [int]$Matches[2]
            $owningPid = [int]$Matches[3]
            if ($linePort -eq $Port -and $owningPid -gt 0) {
                $pids += $owningPid
            }
        }
    }

    return $pids | Select-Object -Unique
}

$pids = Get-ListeningPids -Port $frontendPort
if (-not $pids -or $pids.Count -eq 0) {
    Write-Output "Frontend not running on port $frontendPort."
    exit 0
}

$stoppedAny = $false
foreach ($listeningPid in $pids) {
    try {
        Stop-ProcessTree -RootPid $listeningPid
        Write-Output "Stopped frontend process tree PID=$listeningPid (port $frontendPort)."
        $stoppedAny = $true
    } catch {
        Write-Output "Failed to stop frontend PID=$listeningPid (port $frontendPort): $($_.Exception.Message)"
    }
}

if ($stoppedAny) {
    # Verify the port is actually freed (handles spawned children + slow teardown)
    $deadline = (Get-Date).AddSeconds(5)
    while ((Get-Date) -lt $deadline) {
        $stillListening = Get-ListeningPids -Port $frontendPort
        if (-not $stillListening -or $stillListening.Count -eq 0) {
            exit 0
        }
        Start-Sleep -Milliseconds 200
    }

    $stillListening = Get-ListeningPids -Port $frontendPort
    $pidList = ($stillListening | ForEach-Object { $_.ToString() }) -join ','
    Write-Output "Frontend still listening on port $frontendPort after stop attempt. PIDs=$pidList"
    exit 1
}

exit 1
