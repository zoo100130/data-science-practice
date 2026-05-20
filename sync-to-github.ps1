param(
    [string]$Message
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add -A

$hasChanges = $false
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $hasChanges = $true
}

if ($hasChanges) {
    if ([string]::IsNullOrWhiteSpace($Message)) {
        $Message = "Update coursework files $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    }

    git commit -m $Message
} else {
    Write-Host "No local changes to commit."
}

$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($remote)) {
    git push -u origin main
} else {
    Write-Host "No GitHub remote is configured yet."
    Write-Host "After creating a GitHub repository, run:"
    Write-Host "  git remote add origin https://github.com/<your-account>/<repo-name>.git"
    Write-Host "  .\sync-to-github.ps1"
}
