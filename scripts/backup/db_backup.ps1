# PostgreSQL Daily Backup Script for CK_Missive
# Usage: powershell -ExecutionPolicy Bypass -File db_backup.ps1
# Features: Database backup + Attachments backup

param(
    [int]$RetentionDays = 7,
    [switch]$Verbose = $false,
    [switch]$DatabaseOnly = $false,
    [switch]$AttachmentsOnly = $false,
    [string]$TargetPath = ""  # Optional: NAS/external drive path
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $ProjectRoot "backups\database"
$AttachmentBackupDir = Join-Path $ProjectRoot "backups\attachments"
$UploadsDir = Join-Path $ProjectRoot "backend\uploads"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DateOnly = Get-Date -Format "yyyyMMdd"
$LogDir = Join-Path $ProjectRoot "logs\backup"
$LogFile = Join-Path $LogDir "backup_$DateOnly.log"

# Use custom target path if specified
if ($TargetPath -and (Test-Path $TargetPath)) {
    $BackupDir = Join-Path $TargetPath "database"
    $AttachmentBackupDir = Join-Path $TargetPath "attachments"
    Write-Host "Using custom backup path: $TargetPath" -ForegroundColor Yellow
}

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

    # Clean database backups
    Get-ChildItem -Path $BackupDir -Filter "ck_missive_backup_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item $_.FullName -Force; Log "Deleted DB: $($_.Name)"; $count++ }

    # Clean attachment backups
    Get-ChildItem -Path $AttachmentBackupDir -Filter "attachments_backup_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force; Log "Deleted Attachments: $($_.Name)"; $count++ }

    Log "Cleanup done, deleted $count items"
}

function Do-AttachmentBackup {
    Log "Starting attachments backup..."

    if (!(Test-Path $UploadsDir)) {
        Log "No uploads directory found at: $UploadsDir" "WARN"
        return $true  # Not a failure, just no attachments
    }

    $fileCount = (Get-ChildItem -Path $UploadsDir -Recurse -File -ErrorAction SilentlyContinue).Count
    if ($fileCount -eq 0) {
        Log "No attachment files to backup"
        return $true
    }

    Ensure-Dir $AttachmentBackupDir

    $AttachmentBackupPath = Join-Path $AttachmentBackupDir "attachments_backup_$Timestamp"

    try {
        # Copy uploads directory with structure preserved
        Copy-Item -Path $UploadsDir -Destination $AttachmentBackupPath -Recurse -Force

        $backupSize = [math]::Round((Get-ChildItem -Path $AttachmentBackupPath -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
        Log "Attachments backup completed: $AttachmentBackupPath ($fileCount files, $backupSize MB)"
        return $true
    } catch {
        Log "Attachments backup error: $_" "ERROR"
        return $false
    }
}

function Get-BackupStats {
    $stats = @{
        DatabaseBackups = 0
        AttachmentBackups = 0
        TotalSize = 0
    }

    if (Test-Path $BackupDir) {
        $dbFiles = Get-ChildItem -Path $BackupDir -Filter "ck_missive_backup_*" -ErrorAction SilentlyContinue
        $stats.DatabaseBackups = $dbFiles.Count
        $stats.TotalSize += ($dbFiles | Measure-Object -Property Length -Sum).Sum
    }

    if (Test-Path $AttachmentBackupDir) {
        $attDirs = Get-ChildItem -Path $AttachmentBackupDir -Directory -Filter "attachments_backup_*" -ErrorAction SilentlyContinue
        $stats.AttachmentBackups = $attDirs.Count
        foreach ($dir in $attDirs) {
            $stats.TotalSize += (Get-ChildItem -Path $dir.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
        }
    }

    return $stats
}

Write-Host "=== CK_Missive Full Backup ===" -ForegroundColor Cyan
Write-Host ""

Ensure-Dir $LogDir

$dbSuccess = $true
$attSuccess = $true

# Database backup
if (!$AttachmentsOnly) {
    if (Do-Backup) {
        Log "Database backup successful"
    } else {
        $dbSuccess = $false
    }
}

# Attachments backup
if (!$DatabaseOnly) {
    if (Do-AttachmentBackup) {
        Log "Attachments backup successful"
    } else {
        $attSuccess = $false
    }
}

# Cleanup old backups
Clean-OldBackups

# Show stats
$stats = Get-BackupStats
$totalSizeMB = [math]::Round($stats.TotalSize / 1MB, 2)
Write-Host ""
Write-Host "=== Backup Statistics ===" -ForegroundColor Cyan
Write-Host "Database backups: $($stats.DatabaseBackups)"
Write-Host "Attachment backups: $($stats.AttachmentBackups)"
Write-Host "Total backup size: $totalSizeMB MB"
Write-Host ""

if ($dbSuccess -and $attSuccess) {
    Log "Full backup process completed successfully"
    Write-Host "Backup completed successfully" -ForegroundColor Green
    exit 0
} else {
    Log "Backup process completed with errors"
    Write-Host "Backup completed with errors, check log: $LogFile" -ForegroundColor Yellow
    exit 1
}
