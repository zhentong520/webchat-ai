# Start WeChat group auto-reply
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Group = "测试群1",
    [double]$Interval = 15,
    [switch]$Once,
    [switch]$Echo
)

& "$PSScriptRoot/start_workbuddy_group_reply.ps1" -Groups $Group -Interval $Interval -Once:$Once -Echo:$Echo
