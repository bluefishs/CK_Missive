# Windows Task Scheduler Setup for CK_Missive Daily Backup
# Run as Administrator: powershell -ExecutionPolicy Bypass -File setup_scheduled_task.ps1

param(
    [string]$BackupTime = "02:00",
    [int]$RetentionDays = 7,
    [switch]$Remove = $false
)

$TaskName = "CK_Missive_Daily_Backup"
$TaskDesc = "CK Missive PostgreSQL Daily Backup"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Please run as Administrator" -ForegroundColor Yellow
    exit 1
}

$ScriptDir = Split-Path -Parent $PSScriptRoot
$BackupScript = Join-Path $ScriptDir "backup\db_backup.ps1"

if (!(Test-Path $BackupScript)) {
    Write-Host "Backup script not found: $BackupScript" -ForegroundColor Red
    exit 1
}

if ($Remove) {
    Write-Host "Removing scheduled task: $TaskName..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task removed" -ForegroundColor Green
    exit 0
}

Write-Host "=== Setup CK_Missive Daily Backup ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task Name: $TaskName"
Write-Host "Backup Time: $BackupTime daily"
Write-Host "Retention: $RetentionDays days"
Write-Host "Script: $BackupScript"
Write-Host ""

$timeParts = $BackupTime -split ":"
$hour = [int]$timeParts[0]
$minute = [int]$timeParts[1]

$trigger = New-ScheduledTaskTrigger -Daily -At "$($hour):$($minute)"
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$BackupScript`" -RetentionDays $RetentionDays" `
    -WorkingDirectory (Split-Path $BackupScript)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Description $TaskDesc `
        -Trigger $trigger -Action $action -Settings $settings -Principal $principal -Force | Out-Null

    Write-Host "Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  View: taskschd.msc"
    Write-Host "  Run now: schtasks /run /tn `"$TaskName`""
    Write-Host "  Remove: .\setup_scheduled_task.ps1 -Remove"

    $task = Get-ScheduledTask -TaskName $TaskName
    Write-Host ""
    Write-Host "Status: $($task.State)" -ForegroundColor Cyan
} catch {
    Write-Host "Failed to create task: $_" -ForegroundColor Red
    exit 1
}
