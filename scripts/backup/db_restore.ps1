# PostgreSQL Database Restore Script for CK_Missive
# Usage: .\db_restore.ps1 -List | -Latest | -BackupFile <path>

param(
    [string]$BackupFile,
    [switch]$Latest = $false,
    [switch]$List = $false,
    [switch]$Force = $false
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $ProjectRoot "backups\database"
$LogDir = Join-Path $ProjectRoot "logs\backup"
$DateOnly = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogDir "restore_$DateOnly.log"

$DbUser = "ck_user"
$DbPassword = "ck_password_2024"
$DbName = "ck_documents"
$ContainerName = "ck_missive_postgres"

$EnvFile = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^POSTGRES_USER=(.+)$") { $script:DbUser = $matches[1] }
        if ($_ -match "^POSTGRES_PASSWORD=(.+)$") { $script:DbPassword = $matches[1] }
        if ($_ -match "^POSTGRES_DB=(.+)$") { $script:DbName = $matches[1] }
    }
}

$runningContainer = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
if ($runningContainer) { $ContainerName = $runningContainer }

function Log($msg, $lvl = "INFO") {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$ts] [$lvl] $msg"
    if (Test-Path $LogDir) { Add-Content -Path $LogFile -Value $entry -Encoding UTF8 }
    Write-Host $entry
}

function Get-Backups {
    if (!(Test-Path $BackupDir)) { return @() }
    return Get-ChildItem -Path $BackupDir -Filter "ck_missive_backup_*" | Sort-Object LastWriteTime -Descending
}

if ($List) {
    Write-Host "=== Available Backups ===" -ForegroundColor Cyan
    $backups = Get-Backups
    if ($backups.Count -eq 0) {
        Write-Host "No backups found" -ForegroundColor Yellow
        exit 0
    }
    $i = 1
    foreach ($b in $backups) {
        $size = "{0:N2} KB" -f ($b.Length / 1KB)
        Write-Host "[$i] $($b.Name) - $size - $($b.LastWriteTime)"
        $i++
    }
    Write-Host ""
    Write-Host "Usage: .\db_restore.ps1 -Latest"
    exit 0
}

if ($Latest) {
    $backups = Get-Backups
    if ($backups.Count -eq 0) {
        Write-Host "No backups found" -ForegroundColor Red
        exit 1
    }
    $BackupFile = $backups[0].FullName
    Write-Host "Using latest backup: $BackupFile" -ForegroundColor Cyan
}

if (!$BackupFile) {
    Write-Host "Usage: .\db_restore.ps1 -List | -Latest | -BackupFile <path>"
    exit 1
}

if (!(Test-Path $BackupFile)) {
    Write-Host "Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

Write-Host "=== CK_Missive Database Restore ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will overwrite the current database!" -ForegroundColor Yellow
Write-Host "Backup file: $BackupFile"
Write-Host "Target database: $DbName"
Write-Host ""

if (!$Force) {
    $confirm = Read-Host "Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "Operation cancelled"
        exit 0
    }
}

if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

Log "Starting restore from: $BackupFile"

$dockerCheck = docker ps --filter "name=$ContainerName" --format "{{.Names}}" 2>&1
if ($dockerCheck -ne $ContainerName) {
    Log "Container $ContainerName not running" "ERROR"
    exit 1
}

try {
    $env:PGPASSWORD = $DbPassword
    $sqlContent = Get-Content -Path $BackupFile -Raw -Encoding UTF8
    $sqlContent | docker exec -i $ContainerName psql -U $DbUser -d $DbName 2>&1 | ForEach-Object {
        if ($_ -match "ERROR") { Log $_ "ERROR" }
    }

    Log "Restore completed successfully"
    Write-Host "Restore completed" -ForegroundColor Green
} catch {
    Log "Restore error: $_" "ERROR"
    exit 1
}
