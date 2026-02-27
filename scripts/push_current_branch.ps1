<#
.SYNOPSIS
  Commit local changes and push the current branch to origin.

.DESCRIPTION
  This script is a convenience wrapper around git.
  It stages common project files, creates a commit, and pushes to origin.

  It does NOT change branches or rewrite history.

.PARAMETER Message
  Commit message to use.

.PARAMETER All
  If set, stages ALL changes (git add -A) instead of a curated list.

.EXAMPLE
  .\scripts\push_current_branch.ps1 -Message "fix(windows): service scripts"

.EXAMPLE
  .\scripts\push_current_branch.ps1 -Message "chore: updates" -All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$All
)

$ErrorActionPreference = 'Stop'

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found on PATH: $Name"
    }
}

Require-Command git

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName
Set-Location $ProjectRoot

$branch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    throw "Unable to determine current branch (are you in a git repo?)."
}

Write-Host "Repo: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "Branch: $branch" -ForegroundColor Cyan

# Stage files
if ($All) {
    git add -A
} else {
    # Curated list for this repo; safe to re-run even if some files don't exist.
    $paths = @(
        'pytest.ini',
        'scripts/install.ps1',
        'scripts/service_manager.ps1',
        'scripts/push_current_branch.ps1',
      'scripts/reinstall.ps1',
        'scripts/reinstall_clean.ps1',
        'INSTALL.md',
        'backend/requirements-phase2.txt',
        'backend/tests/tests/conftest.py',
        'backend/src/__init__.py',
        'backend/src/web/__init__.py',
        'backend/src/web/error_handler.py',
        'backend/src/web/middleware_init.py'
    )

    foreach ($p in $paths) {
        if (Test-Path -LiteralPath (Join-Path $ProjectRoot $p)) {
            git add -- $p
        }
    }
}

$status = git status --porcelain
if (-not $status) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
} else {
    git commit -m $Message
}

git push origin $branch
Write-Host "Push complete." -ForegroundColor Green
