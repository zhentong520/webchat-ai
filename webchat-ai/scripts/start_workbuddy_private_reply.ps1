# WorkBuddy private chat auto-reply (mmx / OpenClaw / models.json)
param(
    [string]$Contacts = "Air",
    [double]$Interval = 15,
    [switch]$Once,
    [switch]$Echo
)

$ErrorActionPreference = "Stop"
$Py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "$env:USERPROFILE\.workbuddy\binaries\python\versions\3.13.12\python.exe"
}

$Root = Split-Path $PSScriptRoot -Parent
& $Py "$Root/scripts/unpause_contacts.py" $Contacts

$Script = "$Root/scripts/poll_private_chat.py"
$argsList = @(
    $Script,
    "--contacts", $Contacts,
    "--interval", $Interval
)
if ($Echo) {
    $argsList += "--echo"
} else {
    $argsList += "--workbuddy"
}
if ($Once) { $argsList += "--once" }

$mode = if ($Echo) { "echo-test" } else { "workbuddy-ai" }
Write-Host "Private reply: contacts=$Contacts interval=${Interval}s mode=$mode"
& $Py @argsList
