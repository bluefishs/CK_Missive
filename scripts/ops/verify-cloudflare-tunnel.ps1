# Cloudflare Tunnel 驗證腳本（ADR-0015 / ADR-0016）
#
# 用途：一鍵檢查 missive.cksurvey.tw 整條公網鏈路
# 使用：pwsh -File scripts/ops/verify-cloudflare-tunnel.ps1

param(
    [string]$PublicUrl = "https://missive.cksurvey.tw",
    [string]$LocalUrl = "http://localhost:8001"
)

$ErrorActionPreference = "Continue"
$checks = @()

function Test-Endpoint {
    param([string]$Name, [string]$Url, [string]$Method = "GET", [hashtable]$Headers = @{}, $Body = $null)

    $result = @{ Name = $Name; Url = $Url; Status = "?"; Detail = "" }
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            TimeoutSec = 10
            UseBasicParsing = $true
            SkipHttpErrorCheck = $true
        }
        if ($Headers.Count -gt 0) { $params.Headers = $Headers }
        if ($Body) { $params.Body = $Body; $params.ContentType = "application/json" }

        $r = Invoke-WebRequest @params
        $result.Status = $r.StatusCode
        $result.Detail = if ($r.Content.Length -gt 80) {
            $r.Content.Substring(0, 80) + "..."
        } else { $r.Content }
    } catch {
        $result.Status = "ERR"
        $result.Detail = $_.Exception.Message
    }
    $result
}

Write-Host "`n=== CK Missive Cloudflare Tunnel 驗證 ===" -ForegroundColor Cyan
Write-Host "Public : $PublicUrl" -ForegroundColor Gray
Write-Host "Local  : $LocalUrl`n" -ForegroundColor Gray

# 1. 本機後端是否跑著
$checks += Test-Endpoint "1. 本機 health" "$LocalUrl/api/health"

# 2. CF Tunnel 是否 online
$checks += Test-Endpoint "2. CF Tunnel health" "$PublicUrl/api/health"

# 3. TLS 憑證是否 valid（https 成功即表示 CF 憑證就緒）
$checks += Test-Endpoint "3. TLS 憑證" "$PublicUrl/api/health"

# 4. Manifest POST-only 政策
$checks += Test-Endpoint "4. Manifest (POST)" "$PublicUrl/api/ai/agent/tools" "POST" @{} "{}"

# 5. GET 應被 FastAPI 以 405 拒絕（驗證 POST-only）
$checks += Test-Endpoint "5. Manifest 拒 GET" "$PublicUrl/api/ai/agent/tools"

# 6. Hermes ACP 應要求 X-Service-Token
$acpBody = '{"session_id":"verify","messages":[{"role":"user","content":"ping"}]}'
$checks += Test-Endpoint "6. ACP 無 token" "$PublicUrl/api/hermes/acp" "POST" @{} $acpBody

# 7. Feedback 同樣要求 token
$fbBody = '{"session_id":"v","skill_name":"x","outcome":"success","latency_ms":1}'
$checks += Test-Endpoint "7. Feedback 無 token" "$PublicUrl/api/hermes/feedback" "POST" @{} $fbBody

# 輸出結果
$passed = 0
$failed = 0
foreach ($c in $checks) {
    $expected = switch -Wildcard ($c.Name) {
        "1. 本機*"          { 200 }
        "2. CF Tunnel*"     { 200 }
        "3. TLS*"           { 200 }
        "4. Manifest (POST)*" { 200 }
        "5. Manifest 拒 GET*" { 405 }
        "6. ACP 無 token*"  { @(401, 403) }
        "7. Feedback 無 token*" { @(401, 403) }
    }
    $ok = if ($expected -is [array]) { $expected -contains $c.Status } else { $c.Status -eq $expected }
    $icon = if ($ok) { "✓"; $passed++ } else { "✗"; $failed++ }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("  {0} {1,-30} {2,5}  {3}" -f $icon, $c.Name, $c.Status, $c.Detail) -ForegroundColor $color
}

Write-Host "`n結果：$passed/$($checks.Count) passed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })

if ($failed -gt 0) {
    Write-Host "`n診斷提示：" -ForegroundColor Yellow
    Write-Host "  - 若 1 失敗：Missive backend 未啟動（pm2 list）"
    Write-Host "  - 若 2 失敗：CF Tunnel 未啟動（pm2 logs cloudflared）或 DNS 未生效"
    Write-Host "  - 若 3 失敗：CF Universal SSL 未就緒（等 10 分鐘）"
    Write-Host "  - 若 4/5 失敗：後端 POST-only 政策破損（跑 pytest）"
    Write-Host "  - 若 6/7 失敗：service token 驗證邏輯異常"
    exit 1
}
exit 0
