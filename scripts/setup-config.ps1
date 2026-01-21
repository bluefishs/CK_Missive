# Simple Config Setup Script
param([string]$Action = "setup")

Write-Host "=== CK Missive Configuration Setup ===" -ForegroundColor Cyan

# Copy master config to .env
if (Test-Path ".env.master") {
    Copy-Item ".env.master" ".env" -Force
    Write-Host "Configuration synced successfully!" -ForegroundColor Green
} else {
    Write-Host "Master config file not found!" -ForegroundColor Red
    exit 1
}

# Create necessary directories
$dirs = @("logs", "backend/logs", "frontend/logs", "backend/uploads")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Green
    }
}

Write-Host "Setup completed successfully!" -ForegroundColor Green