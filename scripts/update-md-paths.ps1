param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$files = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter *.md |
    Where-Object { $_.FullName -notmatch "\\node_modules\\" }

$repls = @(
    @{ p = '\./start_backend\.sh';                  r = './scripts/start_backend.sh' },
    @{ p = '\./start_ui\.sh';                       r = './scripts/start_ui.sh' },
    @{ p = 'pytest\s+tests/';                        r = 'pytest backend/tests/' },
    @{ p = 'pytest\s+tests\\';                     r = 'pytest backend/tests\\' }
)

[int]$changed = 0
foreach ($f in $files) {
    $raw = Get-Content -Raw -LiteralPath $f.FullName
    $new = $raw

    foreach ($x in $repls) {
        $new = $new -replace $x.p, $x.r
    }

    if ($new -ne $raw) {
        Set-Content -LiteralPath $f.FullName -Value $new -NoNewline
        $changed++
    }
}

Write-Host "Updated $changed markdown file(s)."
