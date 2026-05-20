param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

$existing = ""
try {
    $existing = git remote get-url origin 2>$null
} catch {
    $existing = ""
}

if ([string]::IsNullOrWhiteSpace($existing)) {
    git remote add origin $RemoteUrl
} else {
    git remote set-url origin $RemoteUrl
}

.\sync-to-github.ps1 -Message "Connect GitHub remote"
