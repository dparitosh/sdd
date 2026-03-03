# ============================================================================
# start_opensearch.ps1 — Manage OpenSearch for the MBSE/SDD vector pipeline
# ============================================================================
#
# Usage:
#   .\scripts\start_opensearch.ps1              # start (foreground / interactive)
#   .\scripts\start_opensearch.ps1 -Detach      # start in background, wait for health
#   .\scripts\start_opensearch.ps1 -Stop        # gracefully stop OpenSearch process
#   .\scripts\start_opensearch.ps1 -Restart     # stop then start (background)
#   .\scripts\start_opensearch.ps1 -Status      # print running/not-running + version
#
# Options:
#   -OpenSearchHome <path>  Override default installation directory
#   -Port <int>             Override default HTTP port (9200)
#   -TimeoutSec <int>       Seconds to wait for startup (default 120)
#
# Notes:
#   * Automatically removes stale node.lock before every start attempt.
#   * Identifies the OpenSearch Java process by its command-line, not process name,
#     so other Java processes (VS Code, etc.) are never touched.
#   * Security plugin is disabled in opensearch.yml (plugins.security.disabled: true),
#     so plain HTTP is used — no TLS/auth required.
# ============================================================================

[CmdletBinding()]
param(
    [switch]$Detach,
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [string]$OpenSearchHome = "",
    [int]$Port = 9200,
    [int]$TimeoutSec = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve installation path
# ---------------------------------------------------------------------------
$defaultHome = "D:\Software\opensearch-3.3.1"
$osHome = if ($OpenSearchHome -ne "") { $OpenSearchHome }
          elseif ($env:OPENSEARCH_HOME -and (Test-Path $env:OPENSEARCH_HOME)) { $env:OPENSEARCH_HOME }
          else { $defaultHome }

$osBat      = Join-Path $osHome "bin\opensearch.bat"
$nodeLock   = Join-Path $osHome "data\nodes\0\node.lock"
$logsDir    = Join-Path $osHome "logs"
$pidFile    = Join-Path $osHome "opensearch.pid"
$baseUrl    = "http://localhost:$Port"

# ---------------------------------------------------------------------------
# Helper: test if OpenSearch HTTP endpoint is reachable
# ---------------------------------------------------------------------------
function Test-OpenSearchRunning {
    try {
        $null = Invoke-RestMethod $baseUrl -TimeoutSec 4 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ---------------------------------------------------------------------------
# Helper: find the OpenSearch Java process by command-line signature
# (avoids killing unrelated java processes such as VS Code language servers)
# ---------------------------------------------------------------------------
function Get-OpenSearchProcess {
    $osHomeNorm = $osHome.TrimEnd('\').ToLower()
    Get-CimInstance Win32_Process -Filter "Name='java.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains($osHomeNorm) }
}

# ---------------------------------------------------------------------------
# Helper: forcibly kill the OpenSearch process (by command-line match)
# ---------------------------------------------------------------------------
function Stop-OpenSearch {
    $procs = Get-OpenSearchProcess
    if (-not $procs) {
        Write-Host "No OpenSearch Java process found — nothing to stop."
        return
    }
    foreach ($p in $procs) {
        Write-Host "  Stopping OpenSearch PID $($p.ProcessId) ..."
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "  PID $($p.ProcessId) terminated."
        } catch {
            # Try taskkill if Stop-Process is denied
            & taskkill /F /PID $p.ProcessId 2>&1 | Out-Null
            Write-Host "  PID $($p.ProcessId) killed via taskkill."
        }
    }
    # Brief pause to let sockets release
    Start-Sleep 2
    # Remove stale lock if it remains
    Remove-StaleLock
}

# ---------------------------------------------------------------------------
# Helper: remove stale node.lock if OpenSearch is NOT running
# ---------------------------------------------------------------------------
function Remove-StaleLock {
    if (Test-Path $nodeLock) {
        $running = $null -ne (Get-OpenSearchProcess)
        if (-not $running) {
            Write-Host "  Removing stale lock: $nodeLock"
            Remove-Item $nodeLock -Force -ErrorAction SilentlyContinue
        }
    }
}

# ---------------------------------------------------------------------------
# Helper: start OpenSearch (background window)
# ---------------------------------------------------------------------------
function Start-OpenSearchBackground {
    if (-not (Test-Path $osBat)) {
        Write-Error "opensearch.bat not found at '$osBat'. Check -OpenSearchHome or OPENSEARCH_HOME."
        exit 1
    }

    # Always clean stale lock before starting
    Remove-StaleLock

    Write-Host "Starting OpenSearch: $osHome"
    $proc = Start-Process `
        -FilePath     $osBat `
        -WorkingDirectory $osHome `
        -WindowStyle  Hidden `
        -PassThru `
        -ErrorAction  Stop

    # Save PID for reference
    $proc.Id | Set-Content $pidFile -Force
    Write-Host "  Launched PID $($proc.Id)  (saved to $pidFile)"

    # Wait for the HTTP endpoint to come up
    Write-Host "  Waiting up to ${TimeoutSec}s for :$Port ..."
    $elapsed = 0
    $ready   = $false
    while ($elapsed -lt $TimeoutSec) {
        Start-Sleep 5
        $elapsed += 5
        if (Test-OpenSearchRunning) {
            $ready = $true
            break
        }
        # Fail-fast if the process already died
        if ($proc.HasExited) {
            Write-Warning "  OpenSearch process exited unexpectedly (exit code $($proc.ExitCode))."
            Write-Warning "  Check logs: $logsDir\opensearch.log"
            exit 1
        }
        Write-Host "  ...${elapsed}s — still waiting"
    }

    if ($ready) {
        $info = Invoke-RestMethod $baseUrl -TimeoutSec 10
        Write-Host ""
        Write-Host "OpenSearch is READY"
        Write-Host "  URL     : $baseUrl"
        Write-Host "  Version : $($info.version.number)"
        Write-Host "  Cluster : $($info.cluster_name)"
    } else {
        Write-Warning "OpenSearch did NOT become ready within ${TimeoutSec}s."
        Write-Warning "Tail of log:"
        $logFile = Join-Path $logsDir "opensearch.log"
        if (Test-Path $logFile) {
            Get-Content $logFile | Select-Object -Last 20 | ForEach-Object { Write-Warning "  $_" }
        }
        exit 1
    }
}

# ============================================================================
# MAIN dispatch
# ============================================================================

switch ($true) {

    # --- -Status ---
    $Status {
        if (Test-OpenSearchRunning) {
            $info = Invoke-RestMethod $baseUrl -TimeoutSec 10
            Write-Host "OpenSearch is RUNNING on :$Port  |  version=$($info.version.number)  cluster=$($info.cluster_name)"
            $p = Get-OpenSearchProcess
            if ($p) { Write-Host "  Java PID: $($p.ProcessId)" }
        } else {
            Write-Host "OpenSearch is NOT RUNNING on :$Port"
            $p = Get-OpenSearchProcess
            if ($p) { Write-Host "  (stale Java process found: PID $($p.ProcessId))" }
        }
        exit 0
    }

    # --- -Stop ---
    $Stop {
        Write-Host "=== Stopping OpenSearch ==="
        Stop-OpenSearch
        if (Test-OpenSearchRunning) {
            Write-Warning "OpenSearch is still responding on :$Port after stop attempt."
            exit 1
        }
        Write-Host "OpenSearch stopped."
        exit 0
    }

    # --- -Restart (background) ---
    $Restart {
        Write-Host "=== Restarting OpenSearch ==="
        if (Test-OpenSearchRunning) {
            Stop-OpenSearch
        } else {
            Remove-StaleLock
        }
        Start-OpenSearchBackground
        exit 0
    }

    # --- -Detach (background start) ---
    $Detach {
        if (Test-OpenSearchRunning) {
            Write-Host "OpenSearch already running on :$Port  (OK)"
            exit 0
        }
        Write-Host "=== Starting OpenSearch (background) ==="
        Start-OpenSearchBackground
        exit 0
    }

    # --- default: interactive (blocks) ---
    default {
        if (Test-OpenSearchRunning) {
            Write-Host "OpenSearch already running on :$Port  (OK)"
            exit 0
        }
        if (-not (Test-Path $osBat)) {
            Write-Error "opensearch.bat not found at '$osBat'."
            exit 1
        }
        Remove-StaleLock
        Write-Host "=== Starting OpenSearch (interactive — Ctrl+C to stop) ==="
        Set-Location $osHome
        & $osBat
    }
}
