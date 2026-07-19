"""SecurityAdminService — 資安管理中心業務邏輯（DDD 標準化，2026-07-20）

標準化 + 檔內異質同工收斂：原 endpoints/security.py 有 3 套略不同的 security score
公式（owasp_summary / notifications〔漏 low〕/ _scan_dict）＝檔內漂移。本 service 提供
單一 compute_security_score SSOT + score_to_grade，並封裝 owasp 儀表板 / 通知衍生組裝。
資料存取委派 SecurityRepository。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.security import SecurityIssue, SecurityScan
from app.repositories.security_repository import SecurityRepository


# ── 純函式 SSOT（可測，取代 3 套漂移公式）──────────────────────────
def compute_security_score(critical: int, high: int, medium: int, low: int = 0) -> int:
    """安全分數 SSOT：critical×25 + high×10 + medium×3 + low×1，下限 0。"""
    return max(0, 100 - critical * 25 - high * 10 - medium * 3 - low * 1)


def score_to_grade(score: int) -> tuple[str, str]:
    """分數 → (等級, 中文標籤)。"""
    if score >= 90:
        return "A", "優良"
    if score >= 70:
        return "B", "尚可"
    if score >= 50:
        return "C", "需改善"
    return "D", "危險"


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


def issue_to_dict(issue: SecurityIssue) -> Dict[str, Any]:
    return {
        "id": issue.id, "project_name": issue.project_name, "title": issue.title,
        "description": issue.description, "severity": issue.severity, "status": issue.status,
        "owasp_category": issue.owasp_category, "cwe_id": issue.cwe_id,
        "cvss_score": issue.cvss_score, "file_path": issue.file_path,
        "line_number": issue.line_number, "remediation": issue.remediation,
        "assigned_to": issue.assigned_to,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
    }


def scan_to_dict(scan: SecurityScan) -> Dict[str, Any]:
    return {
        "id": scan.id, "project_name": scan.project_name, "scan_type": scan.scan_type,
        "status": scan.status, "total_issues": scan.total_issues,
        "critical_count": scan.critical_count, "high_count": scan.high_count,
        "medium_count": scan.medium_count, "low_count": scan.low_count,
        "info_count": scan.info_count,
        # 掃描當下分數（基於該次掃描發現，非即時修復後分數）— 統一 SSOT
        "security_score": compute_security_score(
            scan.critical_count, scan.high_count, scan.medium_count, scan.low_count),
        "duration_seconds": scan.duration_seconds, "created_by": scan.created_by,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
    }


class SecurityAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SecurityRepository(db)

    async def owasp_summary(self) -> Dict[str, Any]:
        owasp_rows = await self.repo.owasp_category_stats()
        owasp_stats = {}
        for row in owasp_rows:
            cat = row.owasp_category
            info = OWASP_CATEGORIES.get(cat, {"name": cat, "nameZh": cat, "color": "#999"})
            owasp_stats[cat] = {**info, "total": row.count, "open": row.open_count}

        severity_dist = await self.repo.open_severity_distribution()
        status_dist = await self.repo.status_distribution()
        total_val = await self.repo.count_total_issues()
        open_val = await self.repo.count_open_issues()

        score = compute_security_score(
            severity_dist.get("critical", 0), severity_dist.get("high", 0),
            severity_dist.get("medium", 0), severity_dist.get("low", 0),
        )
        grade, grade_label = score_to_grade(score)
        last_scan = await self.repo.last_scan()

        return {
            "owasp_standard": "OWASP Top 10",
            "owasp_categories": OWASP_CATEGORIES,
            "owasp_stats": owasp_stats,
            "severity_distribution": severity_dist,
            "total_issues": total_val,
            "open_issues": open_val,
            "resolved_issues": status_dist.get("resolved", 0),
            "false_positive_issues": status_dist.get("false_positive", 0),
            "wont_fix_issues": status_dist.get("wont_fix", 0),
            "security_grade": grade,
            "security_grade_label": grade_label,
            "security_score": score,
            "last_scan": {
                "id": last_scan.id, "scan_type": last_scan.scan_type,
                "total_issues": last_scan.total_issues,
                "security_score": last_scan.security_score,
                "created_at": last_scan.created_at.isoformat() if last_scan and last_scan.created_at else None,
                "created_by": last_scan.created_by,
            } if last_scan else None,
            "scanner_version": "1.0.0",
            "scan_schedule": "每日 02:00 自動掃描",
        }

    async def list_issues(self, q: Any) -> Dict[str, Any]:
        rows, total = await self.repo.list_issues(
            q.project_name, q.status, q.severity, q.page, q.limit)
        return {"items": [issue_to_dict(i) for i in rows], "total": total, "page": q.page}

    async def create_issue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        issue = await self.repo.create_issue(data)
        return {"success": True, "id": issue.id}

    async def update_issue(self, issue_id: int, updates: Dict[str, Any]) -> bool:
        issue = await self.repo.update_issue(issue_id, updates)
        return issue is not None

    async def list_scans(self, q: Any) -> Dict[str, Any]:
        rows = await self.repo.list_scans(q.project_name, q.page, q.limit)
        return {"items": [scan_to_dict(s) for s in rows]}

    async def create_scan(self, data: Any, created_by: Optional[str]) -> Dict[str, Any]:
        scan = await self.repo.create_scan(
            project_name=data.project_name, scan_type=data.scan_type,
            project_path=data.project_path, status="pending", created_by=created_by)
        return {"success": True, "scan_id": scan.id, "status": "pending"}

    async def list_notifications(self, limit: int) -> Dict[str, Any]:
        scans = await self.repo.recent_scans(limit)
        issues = await self.repo.recent_issues(["open", "resolved"], limit)
        items: List[Dict[str, Any]] = []

        if scans:
            latest = scans[0]
            scan_score = compute_security_score(
                latest.critical_count, latest.high_count, latest.medium_count, latest.low_count)
            items.append({
                "id": f"scan-{latest.id}",
                "title": f"安全掃描完成 — 發現 {latest.total_issues} 項待處理",
                "message": f"Critical {latest.critical_count} / High {latest.high_count} / Medium {latest.medium_count} / 掃描評分 {scan_score}",
                "severity": "info" if latest.critical_count == 0 and latest.high_count == 0 else "high",
                "type": "scan",
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
            })

        seen_titles: set = set()
        for issue in issues[:30]:
            dedup_key = f"{issue.severity}:{issue.title}"
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)
            action = "未解決" if issue.status == "open" else "已修復"
            items.append({
                "id": f"issue-{issue.id}",
                "title": f"{action}: {issue.title}",
                "message": f"{issue.file_path or ''}{(' | OWASP ' + issue.owasp_category) if issue.owasp_category else ''}",
                "severity": issue.severity,
                "type": "issue",
                "created_at": issue.updated_at.isoformat() if issue.updated_at else None,
            })

        items.sort(key=lambda x: x.get("created_at", "") or "", reverse=True)
        return {"items": items[:limit], "total": len(items)}
