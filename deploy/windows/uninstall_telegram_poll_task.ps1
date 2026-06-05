$ErrorActionPreference = "Stop"

$TaskName = $env:AGENT_TELEGRAM_TASK_NAME
if (-not $TaskName) {
  $TaskName = "LeoProjects-Agent-Telegram"
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Task removed: $TaskName"
} else {
  Write-Host "Task not found: $TaskName"
}
