# Stop WeChat private auto-reply listener
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Contact,
    [switch]$All,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$Py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "$env:USERPROFILE\.workbuddy\binaries\python\versions\3.13.12\python.exe"
}

$Root = Split-Path $PSScriptRoot -Parent
$Script = "$Root/scripts/stop_listen.py"
$argsList = @($Script)

if ($All) {
    $argsList += "--all-private"
} elseif ($Contact) {
    $argsList += @("--contacts", $Contact)
} else {
    $argsList += "--all-private"
}

if ($NoPause) {
    $argsList += "--no-pause"
}

Write-Host "Stopping private listener..."
& $Py @argsList
