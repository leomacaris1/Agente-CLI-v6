$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$TaskName = $env:AGENT_TELEGRAM_TASK_NAME
if (-not $TaskName) {
  $TaskName = "LeoProjects-Agent-Telegram"
}

$Python = $env:AGENT_PYTHON
if (-not $Python) {
  $Python = "python"
}

$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument "telegram_poll.py" `
  -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Runs the LeoProjects Telegram polling process for agent commands." `
  -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host "Task installed and started: $TaskName"
Write-Host "Repo: $RepoRoot"
