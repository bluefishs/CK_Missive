"""
安全標頭中間件

@version 1.0.0
@date 2026-02-02

提供 OWASP 建議的安全標頭配置:
- X-Frame-Options: 防止點擊劫持
- X-Content-Type-Options: 防止 MIME 類型嗅探
- X-XSS-Protection: 啟用瀏覽器 XSS 過濾器
- Referrer-Policy: 控制 Referrer 資訊
- Permissions-Policy: 控制瀏覽器功能權限

使用方式:
    from app.core.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全標頭中間件

    為所有回應添加安全相關的 HTTP 標頭
    """

    def __init__(
        self,
        app,
        x_frame_options: str = "DENY",
        x_content_type_options: str = "nosniff",
        x_xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str = "geolocation=(), microphone=(), camera=()",
        content_security_policy: str = None,
        content_security_policy_report_only: str = None,
    ):
        super().__init__(app)
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.x_xss_protection = x_xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.content_security_policy = content_security_policy
        self.content_security_policy_report_only = content_security_policy_report_only

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 防止點擊劫持 (Clickjacking)
        response.headers["X-Frame-Options"] = self.x_frame_options

        # 防止 MIME 類型嗅探
        response.headers["X-Content-Type-Options"] = self.x_content_type_options

        # 啟用瀏覽器 XSS 過濾器 (已棄用但仍建議設置)
        response.headers["X-XSS-Protection"] = self.x_xss_protection

        # 控制 Referrer 資訊
        response.headers["Referrer-Policy"] = self.referrer_policy

        # 控制瀏覽器功能權限
        response.headers["Permissions-Policy"] = self.permissions_policy

        # Content Security Policy (如有設置)
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy

        # CSP Report-Only（2026-08-18 新增）
        # 上線一份新的 CSP 之前先跑這個：瀏覽器會照常載入所有資源，
        # 只把「若強制執行會被擋的東西」報到 console 的 securitypolicyviolation。
        # 對這個系統特別重要的一點：前端 bundle 內有
        # `https://www.cksurvey.tw/auth/renew`（SSO 滑動續期），
        # connect-src 若漏掉它，使用者會在 8 小時後被登出而且**沒有任何錯誤畫面** —— 
        # 同一個坑 lvrland 在 2026-08-09 踩過（fetch 被 CSP 擋、只有 console.warn）。
        if self.content_security_policy_report_only:
            response.headers["Content-Security-Policy-Report-Only"] = (
                self.content_security_policy_report_only
            )

        # Reporting-Endpoints（2026-08-19 補）
        # CSP 裡的 `report-to csp-endpoint` 只是**引用一個名字**，
        # 名字要在這個標頭裡定義，否則新式瀏覽器完全不會送報告 ——
        # 而且不會有任何錯誤，就只是安靜地不送。
        # 只在真的有 CSP 時才送，避免對不需要的回應加無意義的標頭。
        if self.content_security_policy or self.content_security_policy_report_only:
            response.headers["Reporting-Endpoints"] = (
                'csp-endpoint="/api/security/csp-report"'
            )

        return response


def get_default_csp() -> str:
    """
    預設 Content Security Policy。

    ⚠️ 2026-08-18 修正：原本這份缺了 `https://www.cksurvey.tw`，
    而前端 bundle 內確實有 `https://www.cksurvey.tw/auth/renew`（SSO 滑動續期）。
    若照原樣強制執行，續期 fetch 會被 connect-src 擋掉 —— 而那個失敗是**靜默的**：
    共享模組只會 console.warn，使用者照樣在 8 小時後被中斷、動作遺失。
    lvrland 在 2026-08-09 就是這樣被擋了兩天（見 CK_Website#docs/SSO-SLIDING-RENEWAL.md）。

    各項來源都對照過 prod bundle 實測：
      accounts.google.com  Google OAuth 登入
      www.cksurvey.tw      SSO IdP（/auth/renew、/auth/verify）
      access.line.me       LINE 登入（redirect 走 form-action，非 connect-src）
      static.cloudflareinsights.com / cloudflareinsights.com
                           CF Web Analytics beacon
                           ⚠️ 這一項是 **Report-Only 實測才抓到的**：靜態分析 dashboard 頁面的
                           實際載入來源時發現它，而第一版 CSP 沒放行 —— 若當初直接上強制，
                           analytics 會靜默失效（beacon 被擋不會有任何畫面異常）。
                           lh3.googleusercontent.com（Google 頭像）則已被 img-src 的 https: 涵蓋。

    script-src 目前仍保留 'unsafe-inline'/'unsafe-eval'（React 生態常見需求）。
    收緊它屬於另一件事，不該和「先讓 CSP 存在」混在一起做 —— 一次改太多，
    出事時分不出是哪一項造成的。
    """
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com "
        "https://apis.google.com https://static.cloudflareinsights.com; "
        # 2026-08-27：補 accounts.google.com —— 這是 **Report-Only 實際回報出來的**，
        #   directive=style-src-elem blocked=https://accounts.google.com/gsi/style
        #   document=https://missive.cksurvey.tw/entry
        # 也就是說，照原樣轉強制會把 Google 登入按鈕的樣式擋掉，而樣式被擋不會有錯誤畫面。
        # 這一項正是 Report-Only 這個機制存在的理由：它抓到了靜態閱讀 CSP 抓不到的東西。
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
        "https://accounts.google.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://www.cksurvey.tw https://accounts.google.com "
        "https://oauth2.googleapis.com https://www.googleapis.com https://cloudflareinsights.com; "
        "frame-src https://accounts.google.com blob:; "  # blob:＝報價單 PDF 預覽 iframe（2026-09-04）
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self' https://accounts.google.com https://access.line.me; "
        # ⚠️ 沒有這一行，Report-Only 就是**無法證偽的**：
        #    瀏覽器算出違規後回報給沒有人，「觀察一段時間確認零違規」永遠會成立。
        #    2026-08-19 實測 prod 標頭才發現原本兩個回報指令都沒有。
        #    report-uri 已廢棄但仍是唯一被所有瀏覽器支援的；report-to 需搭配
        #    Reporting-Endpoints 標頭，兩者並存以涵蓋新舊瀏覽器。
        "report-uri /api/security/csp-report; "
        "report-to csp-endpoint;"
    )
