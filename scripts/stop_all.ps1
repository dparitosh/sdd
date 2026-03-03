# Stop backend, frontend, and OpenSearch (Windows PowerShell)

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

try {
	$stopOpenSearch = Join-Path $repoRoot "scripts\start_opensearch.ps1"
	if (Test-Path $stopOpenSearch) {
		& $stopOpenSearch -Stop
	}
} catch {
	# OpenSearch stop is best-effort
	Write-Host "[WARN] Could not stop OpenSearch: $($_.Exception.Message)" -ForegroundColor Yellow
}

if ($failed) { exit 1 }
exit 0
