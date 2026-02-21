<#
.SYNOPSIS
    API 序列化檢查 Hook
.DESCRIPTION
    檢查 API 端點是否可能直接返回 ORM 模型（未序列化）
    在修改 backend/app/api/endpoints/*.py 後自動執行
.VERSION
    1.0.0
.DATE
    2026-01-21
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$FilePath
)

# 顏色輸出函數
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 檢查是否為 API 端點檔案
function Test-IsApiEndpoint {
    param([string]$Path)
    return $Path -match "backend[\\/]app[\\/]api[\\/]endpoints[\\/].*\.py$"
}

# 檢查檔案中的序列化問題
function Test-SerializationIssues {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-ColorOutput "檔案不存在: $Path" "Yellow"
        return @()
    }

    $content = Get-Content $Path -Raw
    $lines = Get-Content $Path
    $issues = @()

    # 模式 1: .scalars().all() 後直接返回
    # 尋找 scalars().all() 且後續 5 行內有 return 但沒有 model_validate、isoformat 或字典推導
    $lineNumber = 0
    foreach ($line in $lines) {
        $lineNumber++
        if ($line -match '\.scalars\(\)\.all\(\)') {
            $varMatch = [regex]::Match($line, '(\w+)\s*=\s*.*\.scalars\(\)\.all\(\)')
            if ($varMatch.Success) {
                $varName = $varMatch.Groups[1].Value

                # 檢查接下來的 10 行
                $nextLines = $lines[$lineNumber..([Math]::Min($lineNumber + 9, $lines.Count - 1))] -join "`n"

                # 如果直接返回該變數且沒有序列化處理
                if ($nextLines -match "return\s+\{[^}]*[`"']items[`"']\s*:\s*$varName\s*[,\}]") {
                    $issues += @{
                        Line = $lineNumber
                        Message = "可能直接返回 ORM 模型列表: $varName"
                        Severity = "Warning"
                    }
                }
            }
        }
    }

    # 模式 2: 返回字典時沒有處理 datetime
    $lineNumber = 0
    foreach ($line in $lines) {
        $lineNumber++
        # 檢查是否有 datetime 欄位但沒有 .isoformat()
        if ($line -match '["''](created_at|updated_at|deadline|start_date|end_date)["\'']\s*:\s*\w+\.(?:created_at|updated_at|deadline|start_date|end_date)(?!\.isoformat)') {
            $issues += @{
                Line = $lineNumber
                Message = "datetime 欄位可能未使用 .isoformat(): $($Matches[0])"
                Severity = "Info"
            }
        }
    }

    return $issues
}

# 主程式
function Main {
    param([string]$TargetPath)

    Write-ColorOutput "`n========================================" "Cyan"
    Write-ColorOutput "  API 序列化檢查" "Cyan"
    Write-ColorOutput "========================================`n" "Cyan"

    $filesToCheck = @()

    if ($TargetPath -and (Test-Path $TargetPath)) {
        if (Test-IsApiEndpoint $TargetPath) {
            $filesToCheck += $TargetPath
        }
    } else {
        # 檢查所有 API 端點
        $apiDir = Join-Path $PSScriptRoot "..\..\backend\app\api\endpoints"
        if (Test-Path $apiDir) {
            $filesToCheck = Get-ChildItem -Path $apiDir -Filter "*.py" -Recurse |
                Where-Object { $_.Name -notmatch "^__" } |
                Select-Object -ExpandProperty FullName
        }
    }

    if ($filesToCheck.Count -eq 0) {
        Write-ColorOutput "沒有找到需要檢查的 API 端點檔案" "Yellow"
        return 0
    }

    $totalIssues = 0
    $warningCount = 0

    foreach ($file in $filesToCheck) {
        $relativePath = $file -replace [regex]::Escape((Get-Location).Path + "\"), ""
        $issues = Test-SerializationIssues -Path $file

        if ($issues.Count -gt 0) {
            Write-ColorOutput "`n$relativePath" "White"
            foreach ($issue in $issues) {
                $color = switch ($issue.Severity) {
                    "Warning" { "Yellow"; $warningCount++ }
                    "Error" { "Red" }
                    default { "Gray" }
                }
                Write-ColorOutput "  Line $($issue.Line): $($issue.Message)" $color
                $totalIssues++
            }
        }
    }

    Write-ColorOutput "`n----------------------------------------" "Cyan"
    if ($totalIssues -eq 0) {
        Write-ColorOutput "檢查完成: 未發現序列化問題" "Green"
    } else {
        Write-ColorOutput "檢查完成: 發現 $totalIssues 個潛在問題 ($warningCount 個警告)" "Yellow"
        Write-ColorOutput "`n建議措施:" "White"
        Write-ColorOutput "  1. ORM 模型需轉換為字典或使用 Schema.model_validate()" "Gray"
        Write-ColorOutput "  2. datetime 欄位使用 .isoformat() 序列化" "Gray"
        Write-ColorOutput "  3. 參考: .claude/skills/api-serialization.md" "Gray"
    }
    Write-ColorOutput "----------------------------------------`n" "Cyan"

    return $warningCount
}

# 執行
$exitCode = Main -TargetPath $FilePath
exit $exitCode
