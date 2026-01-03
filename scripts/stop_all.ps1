# Stop both backend and frontend (Windows PowerShell)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

$failed = $false

try {
	& (Join-Path $repoRoot "scripts\stop_ui.ps1")
	if ($LASTEXITCODE -ne 0) { $failed = $true }
} catch {
	$failed = $true
}

try {
	& (Join-Path $repoRoot "scripts\stop_backend.ps1")
	if ($LASTEXITCODE -ne 0) { $failed = $true }
} catch {
	$failed = $true
}

if ($failed) { exit 1 }
exit 0
