$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$TaskName = $env:AGENT_WINDOWS_TASK_NAME
if (-not $TaskName) {
  $TaskName = "LeoProjects-Agent-Daemon"
}

$Python = $env:AGENT_PYTHON
if (-not $Python) {
  $Python = "python"
}

$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument "agent_daemon.py" `
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
  -Description "Runs the LeoProjects local agent daemon safely on a recurring interval." `
  -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host "Task installed and started: $TaskName"
Write-Host "Repo: $RepoRoot"
