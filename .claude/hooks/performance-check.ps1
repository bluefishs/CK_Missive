<#
.SYNOPSIS
    效能檢查 Hook - 檢測潛在的 N+1 查詢和效能問題

.DESCRIPTION
    此 hook 在修改後端服務或 API 檔案時觸發，
    自動檢測常見的效能反模式。

.VERSION
    1.0.0

.DATE
    2026-01-22

.RELATED_SKILL
    .claude/skills/database-performance.md
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

function Test-N1QueryPattern {
    param([string]$Content, [string]$FilePath)

    $issues = @()
    $lineNumber = 0

    foreach ($line in $Content -split "`n") {
        $lineNumber++

        # 模式 1: for 迴圈中的 db.execute 或 await db
        if ($line -match "^\s*for\s+.*\s+in\s+.*:") {
            # 檢查接下來的 10 行是否有 db 操作
            $nextLines = ($Content -split "`n")[$lineNumber..($lineNumber + 10)] -join "`n"
            if ($nextLines -match "await\s+db\.(execute|query|get)" -or $nextLines -match "\.scalars\(\)") {
                $issues += @{
                    Line = $lineNumber
                    Pattern = "Potential N+1 query in loop"
                    Suggestion = "Consider using selectinload() or batch query"
                }
            }
        }

        # 模式 2: 沒有使用 selectinload 但存取關聯屬性
        if ($line -match "select\(.*\)(?!.*selectinload)" -and $line -notmatch "func\." -and $line -notmatch "count") {
            # 簡化的檢測，可能需要更精確的分析
        }
    }

    return $issues
}

function Test-MissingPagination {
    param([string]$Content, [string]$FilePath)

    $issues = @()
    $lineNumber = 0

    foreach ($line in $Content -split "`n") {
        $lineNumber++

        # 檢查 select 語句沒有 limit
        if ($line -match "await\s+db\.execute\(.*select\(" -and
            $line -notmatch "\.limit\(" -and
            $line -notmatch "scalar_one" -and
            $line -notmatch "func\.count") {

            # 檢查同一個查詢區塊是否有 limit
            $context = ($Content -split "`n")[([Math]::Max(0, $lineNumber - 5))..([Math]::Min($Content.Length, $lineNumber + 5))] -join "`n"
            if ($context -notmatch "\.limit\(" -and $context -notmatch "\.first\(") {
                $issues += @{
                    Line = $lineNumber
                    Pattern = "Query without pagination"
                    Suggestion = "Add .limit() to prevent loading entire table"
                }
            }
        }
    }

    return $issues
}

function Main {
    Write-Host ""
    Write-Host "=== Performance Check Hook ===" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = 0
    $totalIssues = 0

    # 取得要檢查的檔案
    $filesToCheck = @()

    if ($FilePath -and (Test-Path $FilePath)) {
        $filesToCheck += $FilePath
    } else {
        # 檢查所有後端服務和 API 檔案
        $filesToCheck = Get-ChildItem -Path "backend/app" -Include "*.py" -Recurse |
            Where-Object { $_.FullName -match "(services|endpoints)" } |
            Select-Object -ExpandProperty FullName
    }

    foreach ($file in $filesToCheck) {
        $relativePath = $file -replace [regex]::Escape((Get-Location).Path + "\"), ""
        $content = Get-Content -Path $file -Raw -ErrorAction SilentlyContinue

        if (-not $content) { continue }

        # 執行檢查
        $n1Issues = Test-N1QueryPattern -Content $content -FilePath $file
        $paginationIssues = Test-MissingPagination -Content $content -FilePath $file

        $allIssues = $n1Issues + $paginationIssues

        if ($allIssues.Count -gt 0) {
            Write-Host ""
            Write-ColorOutput "$relativePath" "Warning"

            foreach ($issue in $allIssues) {
                Write-Host "  Line $($issue.Line): $($issue.Pattern)" -ForegroundColor Yellow
                Write-Host "    -> $($issue.Suggestion)" -ForegroundColor Gray
                $totalIssues++
            }
        }
    }

    Write-Host ""
    if ($totalIssues -eq 0) {
        Write-ColorOutput "No performance issues detected" "Success"
    } else {
        Write-ColorOutput "Found $totalIssues potential performance issue(s)" "Warning"
        Write-Host ""
        Write-Host "Reference: .claude/skills/database-performance.md" -ForegroundColor Gray
        $exitCode = 0  # Warning only, don't block
    }

    Write-Host ""
    return $exitCode
}

# 執行主程式
exit (Main)
