"""
資安管理中心 API 端點

基於 OWASP Top 10 2025 標準。
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

    return {
        "owasp_categories": OWASP_CATEGORIES,
        "owasp_stats": owasp_stats,
        "severity_distribution": severity_dist,
        "total_issues": total.scalar() or 0,
        "open_issues": open_count.scalar() or 0,
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
    """列出資安相關的系統通知（從 SystemNotification 查詢）"""
    try:
        from app.extended.models.system import SystemNotification
        stmt = (
            select(SystemNotification)
            .where(SystemNotification.source_table.in_(["security_issues", "security_scans", "security"]))
            .order_by(SystemNotification.created_at.desc())
            .offset((query.page - 1) * query.limit)
            .limit(query.limit)
        )
        result = await db.execute(stmt)
        items = [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "severity": n.severity,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in result.scalars().all()
        ]
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.debug("Security notifications query failed: %s", e)
        return {"items": [], "total": 0}


# ── 安全模式庫 (靜態) ──

@router.post("/patterns", summary="安全模式庫")
async def security_patterns(_user: User = Depends(require_auth())):
    """OWASP 安全編碼最佳實踐"""
    return {
        "patterns": [
            {"category": "A01", "title": "最小權限原則", "description": "每個角色只授予必要的最小權限",
             "example": "require_auth() + require_admin() 雙層驗證"},
            {"category": "A02", "title": "安全預設配置", "description": "所有設定預設為安全狀態",
             "example": "CORS 白名單、CSP Header、HSTS"},
            {"category": "A03", "title": "參數化查詢", "description": "所有 SQL 使用參數化，禁止字串拼接",
             "example": "select(Model).where(Model.id == :id)"},
            {"category": "A05", "title": "密鑰管理", "description": "所有密鑰從環境變數讀取",
             "example": "os.getenv('API_KEY')，禁止硬編碼"},
            {"category": "A06", "title": "依賴更新", "description": "定期執行 npm audit / pip-audit",
             "example": "npm audit --fix && pip-audit"},
            {"category": "A07", "title": "雙 Token 驗證", "description": "service_token.py 支援 dual-token rotation",
             "example": "MCP_SERVICE_TOKEN + MCP_SERVICE_TOKEN_PREV"},
            {"category": "A09", "title": "結構化日誌", "description": "所有安全事件記錄到 structured log",
             "example": "structlog.get_logger() + security event fields"},
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
