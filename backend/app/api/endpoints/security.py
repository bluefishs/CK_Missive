"""
資安管理中心 API 端點（薄委派層）

基於 OWASP Top 10 標準。4 個功能區塊：OWASP 儀表板、問題追蹤、掃描記錄、安全模式庫。

2026-07-20 DDD 標準化：查詢/聚合/score 邏輯抽至 SecurityRepository +
SecurityAdminService，端點只負責 HTTP（參數/認證/錯誤碼）。統一 security score SSOT
（原檔內 3 套漂移公式）。

Version: 1.1.0
Created: 2026-03-27
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.security_admin import IssueCreate, IssueUpdate, ListQuery, ScanCreate
from app.services.system.security_admin_service import SecurityAdminService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["資安管理"])


# ── OWASP 儀表板 ──

@router.post("/owasp-summary", summary="OWASP Top 10 儀表板")
async def owasp_summary(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """OWASP 分類統計 + 嚴重度分佈 + 即時安全分數。"""
    return await SecurityAdminService(db).owasp_summary()


# ── 問題追蹤 CRUD ──

@router.post("/issues/list", summary="問題列表")
async def list_issues(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    return await SecurityAdminService(db).list_issues(query)


@router.post("/issues/create", summary="建立問題")
async def create_issue(
    data: IssueCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    return await SecurityAdminService(db).create_issue(data.model_dump())


@router.post("/issues/update", summary="更新問題")
async def update_issue(
    issue_id: int,
    data: IssueUpdate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    ok = await SecurityAdminService(db).update_issue(
        issue_id, data.model_dump(exclude_unset=True))
    if not ok:
        raise HTTPException(404, "Issue not found")
    return {"success": True}


# ── 掃描記錄 ──

@router.post("/scans/list", summary="掃描記錄列表")
async def list_scans(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    return await SecurityAdminService(db).list_scans(query)


@router.post("/scans/run", summary="執行安全掃描")
async def run_scan(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """立即執行完整安全掃描（程式碼掃描+依賴檢查）。"""
    from app.services.security_scanner import SecurityScanner
    result = await SecurityScanner(db).run_full_scan()
    return {"success": True, **result}


@router.post("/scans/create", summary="手動建立掃描記錄")
async def create_scan(
    data: ScanCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """手動建立掃描記錄。"""
    created_by = _user.username if hasattr(_user, "username") else None
    return await SecurityAdminService(db).create_scan(data, created_by)


# ── 通知管理（系統通知紀錄，非 GitHub Issue） ──

@router.post("/notifications/list", summary="資安通知紀錄")
async def list_security_notifications(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """資安通知紀錄 — 從掃描記錄 + 問題變更自動衍生。"""
    return await SecurityAdminService(db).list_notifications(query.limit)


# ── 安全模式庫 (靜態) ──

@router.post("/patterns", summary="安全模式庫")
async def security_patterns(_user: User = Depends(require_auth())):
    """OWASP 安全編碼最佳實踐 — 完整 Top 10 覆蓋 + CK_Missive 實作規範。"""
    return {
        "patterns": [
            {"category": "A01", "title": "最小權限原則", "severity": "critical",
             "description": "每個角色只授予必要的最小權限。端點必須加認證裝飾器。",
             "example": "Depends(require_auth()) + Depends(require_admin())",
             "reference": "清單 Z-4: 所有端點必須有認證"},
            {"category": "A01", "title": "RBAC 角色權限", "severity": "high",
             "description": "前端 usePermissions() 動態權限檢查，後端 require_admin() 分級。",
             "example": "const { isAdmin } = usePermissions(); if (!isAdmin()) return;",
             "reference": "auth-environment.md"},
            {"category": "A02", "title": "密鑰管理", "severity": "critical",
             "description": "所有密鑰從環境變數讀取，禁止硬編碼。.env 必須在 .gitignore。",
             "example": "os.getenv('API_KEY')，禁止 password='xxx'",
             "reference": "清單 Z-1: 禁止硬編碼密鑰"},
            {"category": "A02", "title": "安全預設配置", "severity": "high",
             "description": "CORS 白名單、HTTPS only、secure cookie、CSP Header。",
             "example": "allow_origins=[...], secure=True, httponly=True",
             "reference": "security-hardening.md"},
            {"category": "A03", "title": "SQL 參數化查詢", "severity": "critical",
             "description": "所有 SQL 使用 ORM 或參數化 text()，禁止 f-string 拼接。",
             "example": "select(Model).where(Model.id == id) 或 text(':id')",
             "reference": "清單 Z-2: SQL 必須參數化"},
            {"category": "A03", "title": "禁止不安全函數", "severity": "high",
             "description": "禁止 eval/exec/pickle.loads/yaml.load。",
             "example": "ast.literal_eval() / json.loads() / yaml.safe_load()",
             "reference": "清單 Z-3: 禁止不安全函數"},
            {"category": "A04", "title": "輸入驗證", "severity": "high",
             "description": "Pydantic Schema 強制型別驗證，API 層不接受任意 dict。",
             "example": "class CreateRequest(BaseModel): name: str = Field(max_length=200)",
             "reference": "development-rules.md 型別 SSOT"},
            {"category": "A05", "title": "密碼雜湊", "severity": "critical",
             "description": "密碼使用 bcrypt 雜湊存儲，禁止明文。Token 使用 HMAC-SHA256。",
             "example": "bcrypt.hashpw() / hmac.compare_digest()",
             "reference": "service_token.py 雙 token 驗證"},
            {"category": "A06", "title": "依賴漏洞管理", "severity": "high",
             "description": "每日 02:00 自動掃描。Critical 3 天內修復。定期 pip-audit。",
             "example": "pip-audit && pip install --upgrade <package>",
             "reference": "清單 Z-5: 依賴漏洞定期更新"},
            {"category": "A07", "title": "Service Token 驗證", "severity": "high",
             "description": "service_token.py 集中管理，支援 dual-token rotation 零停機。",
             "example": "MCP_SERVICE_TOKEN + MCP_SERVICE_TOKEN_PREV",
             "reference": "清單 Z-7: 雙 Token 驗證"},
            {"category": "A07", "title": "Session 管理", "severity": "medium",
             "description": "Redis session TTL 24h，閒置自動登出，CSRF token。",
             "example": "useIdleTimeout(30min) + csrf_token validation",
             "reference": "auth-environment.md"},
            {"category": "A08", "title": "資料序列化安全", "severity": "medium",
             "description": "禁止 pickle 反序列化。API 回傳必須經 Pydantic 驗證。",
             "example": "json.loads() 取代 pickle.loads()",
             "reference": "api-serialization.md"},
            {"category": "A09", "title": "結構化安全日誌", "severity": "medium",
             "description": "所有安全事件記錄到 structlog，含 request_id、user_id、action。",
             "example": "structlog.get_logger().warning('auth_failed', user=..., ip=...)",
             "reference": "structured_logging.py"},
            {"category": "A10", "title": "外部請求防護", "severity": "high",
             "description": "FederationClient 限制目標 URL。TunnelGuard 外網路由守衛。",
             "example": "tunnel_guard.py 白名單 + httpx timeout=10s",
             "reference": "tunnel_guard.py + federation_client.py"},
        ],
    }
