# Start WeChat private auto-reply for a contact
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Contact,
    [double]$Interval = 15,
    [switch]$Once,
    [switch]$Echo
)

$ErrorActionPreference = "Stop"
& "$PSScriptRoot/start_workbuddy_private_reply.ps1" -Contacts $Contact -Interval $Interval -Once:$Once -Echo:$Echo
