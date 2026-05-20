$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$syncScript = Join-Path $repo "sync-to-github.ps1"

function Invoke-Sync {
    & $syncScript
}

Invoke-Sync

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $repo
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, DirectoryName, LastWrite, Size'

$lastRun = Get-Date "2000-01-01"
$action = {
    $path = $Event.SourceEventArgs.FullPath
    if ($path -match "\\.git(\\|$)") {
        return
    }

    $now = Get-Date
    if (($now - $script:lastRun).TotalSeconds -lt 10) {
        return
    }

    $script:lastRun = $now
    Start-Sleep -Seconds 2
    Invoke-Sync
}

$subscriptions = @(
    Register-ObjectEvent $watcher Created -Action $action
    Register-ObjectEvent $watcher Changed -Action $action
    Register-ObjectEvent $watcher Deleted -Action $action
    Register-ObjectEvent $watcher Renamed -Action $action
)

Write-Host "Watching $repo"
Write-Host "Close this PowerShell window to stop automatic syncing."

try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} finally {
    $subscriptions | ForEach-Object { Unregister-Event -SubscriptionId $_.Id }
    $watcher.Dispose()
}
