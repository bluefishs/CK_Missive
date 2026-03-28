"""
資安管理中心 API 端點

基於 OWASP Top 10 標準。
4 個功能區塊：OWASP 儀表板、問題追蹤、掃描記錄、安全模式庫。

Version: 1.0.0
Created: 2026-03-27
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.extended.models.security import SecurityIssue, SecurityScan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["資安管理"])


# ── Schemas ──

class IssueCreate(BaseModel):
    project_name: str = "CK_Missive"
    title: str
    description: Optional[str] = None
    severity: str = "medium"
    owasp_category: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    remediation: Optional[str] = None
    assigned_to: Optional[str] = None


class IssueUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    remediation: Optional[str] = None
    resolved_by: Optional[str] = None


class ScanCreate(BaseModel):
    project_name: str = "CK_Missive"
    scan_type: str = "quick"
    project_path: Optional[str] = None


class ListQuery(BaseModel):
    project_name: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    page: int = 1
    limit: int = 20


# ── OWASP 儀表板 ──

OWASP_CATEGORIES = {
    "A01": {"name": "Broken Access Control", "nameZh": "存取控制漏洞", "color": "#f5222d"},
    "A02": {"name": "Security Misconfiguration", "nameZh": "安全設定錯誤", "color": "#fa8c16"},
    "A03": {"name": "Injection", "nameZh": "注入攻擊", "color": "#fa541c"},
    "A04": {"name": "Insecure Design", "nameZh": "不安全設計", "color": "#eb2f96"},
    "A05": {"name": "Cryptographic Failures", "nameZh": "加密失敗", "color": "#722ed1"},
    "A06": {"name": "Vulnerable Components", "nameZh": "易受攻擊元件", "color": "#2f54eb"},
    "A07": {"name": "Auth Failures", "nameZh": "身分驗證失敗", "color": "#1890ff"},
    "A08": {"name": "Data Integrity Failures", "nameZh": "資料完整性失敗", "color": "#13c2c2"},
    "A09": {"name": "Logging Failures", "nameZh": "日誌監控不足", "color": "#52c41a"},
    "A10": {"name": "SSRF", "nameZh": "伺服器端請求偽造", "color": "#faad14"},
}


@router.post("/owasp-summary", summary="OWASP Top 10 儀表板")
async def owasp_summary(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """OWASP 分類統計 + 嚴重度分佈"""
    # 按 OWASP 類別統計
    owasp_q = await db.execute(
        select(
            SecurityIssue.owasp_category,
            func.count().label("count"),
            func.sum(case((SecurityIssue.status == "open", 1), else_=0)).label("open_count"),
        )
        .where(SecurityIssue.owasp_category.isnot(None))
        .group_by(SecurityIssue.owasp_category)
    )
    owasp_stats = {}
    for row in owasp_q.all():
        cat = row.owasp_category
        info = OWASP_CATEGORIES.get(cat, {"name": cat, "nameZh": cat, "color": "#999"})
        owasp_stats[cat] = {**info, "total": row.count, "open": row.open_count}

    # 嚴重度分佈
    sev_q = await db.execute(
        select(SecurityIssue.severity, func.count())
        .where(SecurityIssue.status == "open")
        .group_by(SecurityIssue.severity)
    )
    severity_dist = {row[0]: row[1] for row in sev_q.all()}

    # 總計
    total = await db.execute(select(func.count()).select_from(SecurityIssue))
    open_count = await db.execute(
        select(func.count()).select_from(SecurityIssue).where(SecurityIssue.status == "open")
    )

    total_val = total.scalar() or 0
    open_val = open_count.scalar() or 0

    # 即時安全分數（基於 open issues，非掃描快照）
    score = max(0, 100
        - severity_dist.get("critical", 0) * 25
        - severity_dist.get("high", 0) * 10
        - severity_dist.get("medium", 0) * 3
        - severity_dist.get("low", 0) * 1)

    # 安全等級
    if score >= 90:
        grade, grade_label = "A", "優良"
    elif score >= 70:
        grade, grade_label = "B", "尚可"
    elif score >= 50:
        grade, grade_label = "C", "需改善"
    else:
        grade, grade_label = "D", "危險"

    # 最近掃描
    last_scan_q = await db.execute(
        select(SecurityScan).order_by(SecurityScan.created_at.desc()).limit(1)
    )
    last_scan = last_scan_q.scalar_one_or_none()

    return {
        "owasp_standard": "OWASP Top 10",
        "owasp_categories": OWASP_CATEGORIES,
        "owasp_stats": owasp_stats,
        "severity_distribution": severity_dist,
        "total_issues": total_val,
        "open_issues": open_val,
        "security_grade": grade,
        "security_grade_label": grade_label,
        "security_score": score,
        "last_scan": {
            "id": last_scan.id,
            "scan_type": last_scan.scan_type,
            "total_issues": last_scan.total_issues,
            "security_score": last_scan.security_score,
            "created_at": last_scan.created_at.isoformat() if last_scan and last_scan.created_at else None,
            "created_by": last_scan.created_by,
        } if last_scan else None,
        "scanner_version": "1.0.0",
        "scan_schedule": "每日 02:00 自動掃描",
    }


# ── 問題追蹤 CRUD ──

@router.post("/issues/list", summary="問題列表")
async def list_issues(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    stmt = select(SecurityIssue)
    if query.project_name:
        stmt = stmt.where(SecurityIssue.project_name == query.project_name)
    if query.status:
        stmt = stmt.where(SecurityIssue.status == query.status)
    if query.severity:
        stmt = stmt.where(SecurityIssue.severity == query.severity)

    count_q = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    stmt = stmt.order_by(SecurityIssue.created_at.desc())
    stmt = stmt.offset((query.page - 1) * query.limit).limit(query.limit)
    result = await db.execute(stmt)

    return {
        "items": [_issue_dict(i) for i in result.scalars().all()],
        "total": total,
        "page": query.page,
    }


@router.post("/issues/create", summary="建立問題")
async def create_issue(
    data: IssueCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    issue = SecurityIssue(**data.model_dump())
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return {"success": True, "id": issue.id}


@router.post("/issues/update", summary="更新問題")
async def update_issue(
    issue_id: int,
    data: IssueUpdate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    issue = await db.get(SecurityIssue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found")
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] == "resolved":
        updates["resolved_at"] = datetime.now()
    for k, v in updates.items():
        setattr(issue, k, v)
    await db.commit()
    return {"success": True}


# ── 掃描記錄 ──

@router.post("/scans/list", summary="掃描記錄列表")
async def list_scans(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    stmt = select(SecurityScan).order_by(SecurityScan.created_at.desc())
    if query.project_name:
        stmt = stmt.where(SecurityScan.project_name == query.project_name)
    stmt = stmt.offset((query.page - 1) * query.limit).limit(query.limit)
    result = await db.execute(stmt)
    return {"items": [_scan_dict(s) for s in result.scalars().all()]}


@router.post("/scans/run", summary="執行安全掃描")
async def run_scan(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """立即執行完整安全掃描（程式碼掃描+依賴檢查）"""
    from app.services.security_scanner import SecurityScanner
    scanner = SecurityScanner(db)
    result = await scanner.run_full_scan()
    return {"success": True, **result}


@router.post("/scans/create", summary="手動建立掃描記錄")
async def create_scan(
    data: ScanCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """手動建立掃描記錄"""
    scan = SecurityScan(
        project_name=data.project_name,
        scan_type=data.scan_type,
        project_path=data.project_path,
        status="pending",
        created_by=_user.username if hasattr(_user, 'username') else None,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return {"success": True, "scan_id": scan.id, "status": "pending"}


# ── 通知管理（系統通知紀錄，非 GitHub Issue） ──

@router.post("/notifications/list", summary="資安通知紀錄")
async def list_security_notifications(
    query: ListQuery = ListQuery(),
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """資安通知紀錄 — 從掃描記錄+問題變更自動產生"""
    # 從掃描歷史產生通知
    scan_stmt = (
        select(SecurityScan)
        .order_by(SecurityScan.created_at.desc())
        .limit(query.limit)
    )
    scans = (await db.execute(scan_stmt)).scalars().all()

    # 從最近解決/新增的問題產生通知
    issue_stmt = (
        select(SecurityIssue)
        .where(SecurityIssue.status.in_(["open", "resolved"]))
        .order_by(SecurityIssue.updated_at.desc())
        .limit(query.limit)
    )
    issues = (await db.execute(issue_stmt)).scalars().all()

    items = []
    for scan in scans:
        severity = "critical" if scan.critical_count > 0 else "high" if scan.high_count > 0 else "info"
        items.append({
            "id": f"scan-{scan.id}",
            "title": f"安全掃描完成 — {scan.project_name}",
            "message": f"發現 {scan.total_issues} 個問題 (C:{scan.critical_count} H:{scan.high_count} M:{scan.medium_count}), 安全分數: {scan.security_score or 0:.0f}",
            "severity": severity,
            "type": "scan",
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        })
    for issue in issues[:10]:
        action = "新發現" if issue.status == "open" else "已修復"
        items.append({
            "id": f"issue-{issue.id}",
            "title": f"[{issue.severity}] {action}: {issue.title}",
            "message": f"{issue.file_path or ''} | OWASP {issue.owasp_category or ''}",
            "severity": issue.severity,
            "type": "issue",
            "created_at": issue.updated_at.isoformat() if issue.updated_at else None,
        })

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": items[:query.limit], "total": len(items)}


# ── 安全模式庫 (靜態) ──

@router.post("/patterns", summary="安全模式庫")
async def security_patterns(_user: User = Depends(require_auth())):
    """OWASP 安全編碼最佳實踐 — 完整 Top 10 覆蓋 + CK_Missive 實作規範"""
    return {
        "patterns": [
            # A01: Broken Access Control
            {"category": "A01", "title": "最小權限原則", "severity": "critical",
             "description": "每個角色只授予必要的最小權限。端點必須加認證裝飾器。",
             "example": "Depends(require_auth()) + Depends(require_admin())",
             "reference": "清單 Z-4: 所有端點必須有認證"},
            {"category": "A01", "title": "RBAC 角色權限", "severity": "high",
             "description": "前端 usePermissions() 動態權限檢查，後端 require_admin() 分級。",
             "example": "const { isAdmin } = usePermissions(); if (!isAdmin()) return;",
             "reference": "auth-environment.md"},

            # A02: Security Misconfiguration
            {"category": "A02", "title": "密鑰管理", "severity": "critical",
             "description": "所有密鑰從環境變數讀取，禁止硬編碼。.env 必須在 .gitignore。",
             "example": "os.getenv('API_KEY')，禁止 password='xxx'",
             "reference": "清單 Z-1: 禁止硬編碼密鑰"},
            {"category": "A02", "title": "安全預設配置", "severity": "high",
             "description": "CORS 白名單、HTTPS only、secure cookie、CSP Header。",
             "example": "allow_origins=[...], secure=True, httponly=True",
             "reference": "security-hardening.md"},

            # A03: Injection
            {"category": "A03", "title": "SQL 參數化查詢", "severity": "critical",
             "description": "所有 SQL 使用 ORM 或參數化 text()，禁止 f-string 拼接。",
             "example": "select(Model).where(Model.id == id) 或 text(':id')",
             "reference": "清單 Z-2: SQL 必須參數化"},
            {"category": "A03", "title": "禁止不安全函數", "severity": "high",
             "description": "禁止 eval/exec/pickle.loads/yaml.load。",
             "example": "ast.literal_eval() / json.loads() / yaml.safe_load()",
             "reference": "清單 Z-3: 禁止不安全函數"},

            # A04: Insecure Design
            {"category": "A04", "title": "輸入驗證", "severity": "high",
             "description": "Pydantic Schema 強制型別驗證，API 層不接受任意 dict。",
             "example": "class CreateRequest(BaseModel): name: str = Field(max_length=200)",
             "reference": "development-rules.md 型別 SSOT"},

            # A05: Cryptographic Failures
            {"category": "A05", "title": "密碼雜湊", "severity": "critical",
             "description": "密碼使用 bcrypt 雜湊存儲，禁止明文。Token 使用 HMAC-SHA256。",
             "example": "bcrypt.hashpw() / hmac.compare_digest()",
             "reference": "service_token.py 雙 token 驗證"},

            # A06: Vulnerable Components
            {"category": "A06", "title": "依賴漏洞管理", "severity": "high",
             "description": "每日 02:00 自動掃描。Critical 3 天內修復。定期 pip-audit。",
             "example": "pip-audit && pip install --upgrade <package>",
             "reference": "清單 Z-5: 依賴漏洞定期更新"},

            # A07: Auth Failures
            {"category": "A07", "title": "Service Token 驗證", "severity": "high",
             "description": "service_token.py 集中管理，支援 dual-token rotation 零停機。",
             "example": "MCP_SERVICE_TOKEN + MCP_SERVICE_TOKEN_PREV",
             "reference": "清單 Z-7: 雙 Token 驗證"},
            {"category": "A07", "title": "Session 管理", "severity": "medium",
             "description": "Redis session TTL 24h，閒置自動登出，CSRF token。",
             "example": "useIdleTimeout(30min) + csrf_token validation",
             "reference": "auth-environment.md"},

            # A08: Data Integrity Failures
            {"category": "A08", "title": "資料序列化安全", "severity": "medium",
             "description": "禁止 pickle 反序列化。API 回傳必須經 Pydantic 驗證。",
             "example": "json.loads() 取代 pickle.loads()",
             "reference": "api-serialization.md"},

            # A09: Logging Failures
            {"category": "A09", "title": "結構化安全日誌", "severity": "medium",
             "description": "所有安全事件記錄到 structlog，含 request_id、user_id、action。",
             "example": "structlog.get_logger().warning('auth_failed', user=..., ip=...)",
             "reference": "structured_logging.py"},

            # A10: SSRF
            {"category": "A10", "title": "外部請求防護", "severity": "high",
             "description": "FederationClient 限制目標 URL。TunnelGuard 外網路由守衛。",
             "example": "tunnel_guard.py 白名單 + httpx timeout=10s",
             "reference": "tunnel_guard.py + federation_client.py"},
        ],
    }


# ── Helpers ──

def _issue_dict(issue: SecurityIssue) -> dict:
    return {
        "id": issue.id,
        "project_name": issue.project_name,
        "title": issue.title,
        "description": issue.description,
        "severity": issue.severity,
        "status": issue.status,
        "owasp_category": issue.owasp_category,
        "cwe_id": issue.cwe_id,
        "cvss_score": issue.cvss_score,
        "file_path": issue.file_path,
        "line_number": issue.line_number,
        "remediation": issue.remediation,
        "assigned_to": issue.assigned_to,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
    }


def _scan_dict(scan: SecurityScan) -> dict:
    return {
        "id": scan.id,
        "project_name": scan.project_name,
        "scan_type": scan.scan_type,
        "status": scan.status,
        "total_issues": scan.total_issues,
        "critical_count": scan.critical_count,
        "high_count": scan.high_count,
        "medium_count": scan.medium_count,
        "low_count": scan.low_count,
        "info_count": scan.info_count,
        "security_score": scan.security_score,
        "duration_seconds": scan.duration_seconds,
        "created_by": scan.created_by,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
    }
