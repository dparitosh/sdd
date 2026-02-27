# Stop both backend and frontend (Windows PowerShell)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

$failed = $false

try {
	$stopUi = Join-Path $repoRoot "scripts\stop_ui.ps1"
	& $stopUi
	if (-not $?) { $failed = $true }
} catch {
	$failed = $true
}

try {
	$stopBackend = Join-Path $repoRoot "scripts\stop_backend.ps1"
	& $stopBackend
	if (-not $?) { $failed = $true }
} catch {
	$failed = $true
}

if ($failed) { exit 1 }
exit 0
