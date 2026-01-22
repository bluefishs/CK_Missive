<#
.SYNOPSIS
    Link ID 驗證 Hook - 檢查關聯端點是否正確返回 link_id

.DESCRIPTION
    此 hook 檢測 API 端點中的關聯資料返回結構，
    確保所有關聯記錄都包含 link_id 欄位。

.VERSION
    1.0.0

.DATE
    2026-01-22

.RELATED_SKILL
    docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md
#>

param(
    [string]$FilePath = ""
)

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Level = "Info"
    )

    switch ($Level) {
        "Error"   { Write-Host "[ERROR] $Message" -ForegroundColor Red }
        "Warning" { Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
        "Success" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "Info"    { Write-Host "[INFO] $Message" -ForegroundColor Gray }
    }
}

function Test-LinkIdPresence {
    param([string]$Content, [string]$FilePath)

    $issues = @()
    $lineNumber = 0

    # 關聯相關的關鍵字
    $linkPatterns = @(
        "linked_projects",
        "linked_documents",
        "linked_dispatches",
        "dispatch_links",
        "document_links",
        "project_links"
    )

    foreach ($line in $Content -split "`n") {
        $lineNumber++

        # 檢查是否有關聯資料的構建
        foreach ($pattern in $linkPatterns) {
            if ($line -match $pattern) {
                # 檢查該區域是否有 link_id
                $context = ($Content -split "`n")[([Math]::Max(0, $lineNumber - 3))..([Math]::Min($Content.Length - 1, $lineNumber + 10))] -join "`n"

                # 如果在構建字典但沒有 link_id
                if ($context -match "\{" -and $context -notmatch "'link_id'" -and $context -notmatch '"link_id"' -and $context -notmatch "link_id=") {
                    # 排除 import 語句和註解
                    if ($line -notmatch "^#" -and $line -notmatch "import" -and $line -notmatch "from ") {
                        $issues += @{
                            Line = $lineNumber
                            Pattern = "Link data may be missing link_id"
                            Context = $pattern
                            Suggestion = "Ensure link_id is included in the response"
                        }
                    }
                }
            }
        }

        # 檢查危險的回退邏輯
        if ($line -match "link_id.*\?\?.*\.id" -or $line -match "link_id.*or.*\.id") {
            $issues += @{
                Line = $lineNumber
                Pattern = "Dangerous fallback logic detected"
                Context = "link_id ?? id"
                Suggestion = "Remove fallback, require link_id explicitly"
            }
        }
    }

    return $issues
}

function Main {
    Write-Host ""
    Write-Host "=== Link ID Validation Hook ===" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = 0
    $totalIssues = 0

    # 取得要檢查的檔案
    $filesToCheck = @()

    if ($FilePath -and (Test-Path $FilePath)) {
        $filesToCheck += $FilePath
    } else {
        # 檢查所有 API 端點檔案
        $filesToCheck = Get-ChildItem -Path "backend/app/api/endpoints" -Include "*.py" -Recurse |
            Select-Object -ExpandProperty FullName
    }

    foreach ($file in $filesToCheck) {
        $relativePath = $file -replace [regex]::Escape((Get-Location).Path + "\"), ""
        $content = Get-Content -Path $file -Raw -ErrorAction SilentlyContinue

        if (-not $content) { continue }

        # 只檢查包含關聯操作的檔案
        if ($content -notmatch "link" -and $content -notmatch "Link") { continue }

        $issues = Test-LinkIdPresence -Content $content -FilePath $file

        if ($issues.Count -gt 0) {
            Write-Host ""
            Write-ColorOutput "$relativePath" "Warning"

            foreach ($issue in $issues) {
                Write-Host "  Line $($issue.Line): $($issue.Pattern)" -ForegroundColor Yellow
                Write-Host "    Context: $($issue.Context)" -ForegroundColor Gray
                Write-Host "    -> $($issue.Suggestion)" -ForegroundColor Gray
                $totalIssues++
            }
        }
    }

    Write-Host ""
    if ($totalIssues -eq 0) {
        Write-ColorOutput "Link ID validation passed" "Success"
    } else {
        Write-ColorOutput "Found $totalIssues potential link_id issue(s)" "Warning"
        Write-Host ""
        Write-Host "Reference: docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md" -ForegroundColor Gray
    }

    Write-Host ""
    return $exitCode
}

# 執行主程式
exit (Main)
