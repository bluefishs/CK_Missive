# 將開發用自簽憑證加入 Windows 信任根 CA
# 在內網各工作站執行一次（需管理員權限）後，瀏覽器不再顯示不安全警告
#
# 用法 (管理員 PowerShell):
#   .\scripts\dev\trust-dev-cert.ps1

$certPath = Join-Path $PSScriptRoot "..\..\frontend\certs\dev-cert.pem"
$certPath = (Resolve-Path $certPath).Path

if (-not (Test-Path $certPath)) {
    Write-Host "[ERROR] 找不到憑證: $certPath" -ForegroundColor Red
    Write-Host "請先執行前端開發伺服器以生成憑證" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== CK_Missive 開發憑證信任工具 ===" -ForegroundColor Cyan
Write-Host "憑證路徑: $certPath"
Write-Host ""

# 檢查管理員權限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] 需要管理員權限，請以「系統管理員身分執行」PowerShell" -ForegroundColor Red
    exit 1
}

try {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certPath)
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open("ReadWrite")
    $store.Add($cert)
    $store.Close()

    Write-Host "[OK] 憑證已加入信任根 CA" -ForegroundColor Green
    Write-Host "請重新啟動瀏覽器後生效" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "涵蓋的 IP:" -ForegroundColor Cyan
    Write-Host "  - https://localhost:3000"
    Write-Host "  - https://192.168.50.210:3000"
    Write-Host "  - https://192.168.50.35:3000"
    Write-Host "  - https://192.168.50.38:3000"
} catch {
    Write-Host "[ERROR] 加入憑證失敗: $_" -ForegroundColor Red
    exit 1
}
