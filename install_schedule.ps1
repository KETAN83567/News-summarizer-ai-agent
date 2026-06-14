param(
    [string]$PythonPath = "",
    [string]$TaskName = "Personal Morning News Agent",
    [string]$RunAt = "07:00",
    [switch]$InstallAlerts
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $PythonPath) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "Python was not found on PATH. Run again with -PythonPath 'C:\path\to\python.exe'."
    }
    $PythonPath = $PythonCommand.Source
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$ProjectDir\main.py`"" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Builds and emails a personalized intelligence briefing every morning." `
    -Force | Out-Null

Write-Host "Installed '$TaskName' for $RunAt every day."
Write-Host "The task uses the computer's local timezone and will run after wake-up if 7:00 was missed."

if ($InstallAlerts) {
    $AlertTaskName = "$TaskName - Alerts"
    $AlertAction = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument "`"$ProjectDir\main.py`" alert-scan" `
        -WorkingDirectory $ProjectDir
    $AlertTrigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date).Date.AddMinutes(5) `
        -RepetitionInterval (New-TimeSpan -Minutes 30) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
    Register-ScheduledTask `
        -TaskName $AlertTaskName `
        -Action $AlertAction `
        -Trigger $AlertTrigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Checks for corroborated, unusually important breaking developments." `
        -Force | Out-Null
    Write-Host "Installed '$AlertTaskName' to scan every 30 minutes."
}
