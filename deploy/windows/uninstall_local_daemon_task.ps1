$ErrorActionPreference = "Stop"

$TaskName = $env:AGENT_WINDOWS_TASK_NAME
if (-not $TaskName) {
  $TaskName = "LeoProjects-Agent-Daemon"
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Task removed: $TaskName"
} else {
  Write-Host "Task not found: $TaskName"
}
