# PostgreSQL Daily Backup Script for CK_Missive
# Usage: powershell -ExecutionPolicy Bypass -File db_backup.ps1

param(
    [int]$RetentionDays = 7,
    [switch]$Verbose = $false
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $ProjectRoot "backups\database"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DateOnly = Get-Date -Format "yyyyMMdd"
$LogDir = Join-Path $ProjectRoot "logs\backup"
$LogFile = Join-Path $LogDir "backup_$DateOnly.log"

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
        if ($_ -match "^COMPOSE_PROJECT_NAME=(.+)$") { $script:ContainerName = "$($matches[1])_postgres" }
    }
}

$runningContainer = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
if ($runningContainer) { $ContainerName = $runningContainer }

function Ensure-Dir($path) {
    if (!(Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

function Log($msg, $lvl = "INFO") {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$ts] [$lvl] $msg"
    if (Test-Path (Split-Path $LogFile)) { Add-Content -Path $LogFile -Value $entry -Encoding UTF8 }
    if ($Verbose -or $lvl -eq "ERROR") { Write-Host $entry }
}

function Do-Backup {
    Log "Starting database backup..."
    Log "Backup dir: $BackupDir"
    Log "Container: $ContainerName"

    Ensure-Dir $BackupDir
    Ensure-Dir $LogDir

    $dockerCheck = docker ps --filter "name=$ContainerName" --format "{{.Names}}" 2>&1
    if ($dockerCheck -ne $ContainerName) {
        Log "ERROR: Container $ContainerName not running" "ERROR"
        return $false
    }

    Log "Container running, executing pg_dump..."

    $BackupFile = Join-Path $BackupDir "ck_missive_backup_$Timestamp.sql"

    try {
        $env:PGPASSWORD = $DbPassword
        $result = docker exec $ContainerName pg_dump -U $DbUser -d $DbName --no-owner --no-acl 2>&1

        if ($LASTEXITCODE -eq 0) {
            $result | Out-File -FilePath $BackupFile -Encoding UTF8
            $size = [math]::Round((Get-Item $BackupFile).Length / 1KB, 2)
            Log "Backup completed: $BackupFile ($size KB)"
            return $true
        } else {
            Log "pg_dump failed: $result" "ERROR"
            return $false
        }
    } catch {
        Log "Backup error: $_" "ERROR"
        return $false
    }
}

function Clean-OldBackups {
    Log "Cleaning backups older than $RetentionDays days..."
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $count = 0
    Get-ChildItem -Path $BackupDir -Filter "ck_missive_backup_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item $_.FullName -Force; Log "Deleted: $($_.Name)"; $count++ }
    Log "Cleanup done, deleted $count files"
}

Write-Host "=== CK_Missive Database Backup ===" -ForegroundColor Cyan
Write-Host ""

Ensure-Dir $LogDir

if (Do-Backup) {
    Clean-OldBackups
    Log "Backup process completed"
    Write-Host "Backup completed successfully" -ForegroundColor Green
    exit 0
} else {
    Log "Backup process failed"
    Write-Host "Backup failed, check log: $LogFile" -ForegroundColor Red
    exit 1
}
