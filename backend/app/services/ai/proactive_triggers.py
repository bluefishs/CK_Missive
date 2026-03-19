"""
Proactive Triggers — 主動觸發通知服務

定時掃描資料庫，偵測需要通知的事件：
1. 截止日提醒：公文/案件接近或已逾截止日
2. 異常偵測：系統健康異常、資料品質下降

對標 OpenClaw proactive-agent 的主動通知模式。

Version: 1.0.0
Created: 2026-03-15
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class TriggerAlert:
    """觸發警報"""
    alert_type: str       # deadline_warning, deadline_overdue, data_quality, system_health
    severity: str         # info, warning, critical
    title: str
    message: str
    entity_type: str      # document, project, dispatch, system
    entity_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProactiveTriggerService:
    """
    主動觸發服務

    Usage:
        service = ProactiveTriggerService(db)
        alerts = await service.scan_all()
        # alerts: List[TriggerAlert]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_all(
        self,
        deadline_days: int = 7,
    ) -> List[TriggerAlert]:
        """掃描所有觸發條件，回傳警報列表"""
        alerts: List[TriggerAlert] = []

        # 1. 公文截止日
        doc_alerts = await self.check_document_deadlines(deadline_days)
        alerts.extend(doc_alerts)

        # 2. 案件逾期
        project_alerts = await self.check_project_deadlines(deadline_days)
        alerts.extend(project_alerts)

        # 3. PM/ERP 觸發 (里程碑逾期、請款逾期、發票催開、外包付款)
        from app.services.ai.proactive_triggers_erp import ERPTriggerScanner
        erp_scanner = ERPTriggerScanner(self.db)
        erp_alerts = await erp_scanner.scan_all(deadline_days)
        alerts.extend(erp_alerts)

        # 7. 資料品質
        quality_alerts = await self.check_data_quality()
        alerts.extend(quality_alerts)

        # 8. 主動推薦 (新公文 ↔ 使用者興趣匹配)
        rec_alerts = await self.check_recommendations()
        alerts.extend(rec_alerts)

        # 9. 未摘要公文 (NER 完成但無 AI 摘要)
        unsummarized_alerts = await self.check_unsummarized_documents()
        alerts.extend(unsummarized_alerts)

        logger.info(
            "Proactive scan complete: %d alerts (%d critical, %d warning)",
            len(alerts),
            sum(1 for a in alerts if a.severity == "critical"),
            sum(1 for a in alerts if a.severity == "warning"),
        )

        return alerts

    async def check_document_deadlines(
        self,
        days_ahead: int = 7,
    ) -> List[TriggerAlert]:
        """
        檢查行事曆事件截止日（公文截止提醒）。

        OfficialDocument 本身沒有 deadline 欄位，
        因此使用 DocumentCalendarEvent 的 end_date 作為截止日依據。
        """
        from app.extended.models.calendar import DocumentCalendarEvent

        today = date.today()
        deadline_threshold = today + timedelta(days=days_ahead)
        alerts: List[TriggerAlert] = []

        # 已逾期的未完成事件
        overdue_result = await self.db.execute(
            select(
                DocumentCalendarEvent.id,
                DocumentCalendarEvent.title,
                DocumentCalendarEvent.end_date,
                DocumentCalendarEvent.document_id,
            )
            .where(
                DocumentCalendarEvent.end_date < today,
                DocumentCalendarEvent.end_date.isnot(None),
                DocumentCalendarEvent.status != "completed",
            )
            .order_by(DocumentCalendarEvent.end_date)
            .limit(20)
        )
        for row in overdue_result.all():
            end = row.end_date.date() if hasattr(row.end_date, 'date') else row.end_date
            days_over = (today - end).days
            alerts.append(TriggerAlert(
                alert_type="deadline_overdue",
                severity="critical",
                title=f"事件已逾期 {days_over} 天",
                message=f"「{row.title or '未命名事件'}」已逾期 {days_over} 天",
                entity_type="document",
                entity_id=row.document_id,
                metadata={"days_overdue": days_over, "deadline": str(row.end_date)},
            ))

        # 即將到期事件
        upcoming_result = await self.db.execute(
            select(
                DocumentCalendarEvent.id,
                DocumentCalendarEvent.title,
                DocumentCalendarEvent.end_date,
                DocumentCalendarEvent.document_id,
            )
            .where(
                DocumentCalendarEvent.end_date >= today,
                DocumentCalendarEvent.end_date <= deadline_threshold,
                DocumentCalendarEvent.end_date.isnot(None),
                DocumentCalendarEvent.status != "completed",
            )
            .order_by(DocumentCalendarEvent.end_date)
            .limit(20)
        )
        for row in upcoming_result.all():
            end = row.end_date.date() if hasattr(row.end_date, 'date') else row.end_date
            days_left = (end - today).days
            alerts.append(TriggerAlert(
                alert_type="deadline_warning",
                severity="warning" if days_left <= 3 else "info",
                title=f"事件將於 {days_left} 天內到期",
                message=f"「{row.title or '未命名事件'}」將於 {row.end_date} 到期",
                entity_type="document",
                entity_id=row.document_id,
                metadata={"days_remaining": days_left, "deadline": str(row.end_date)},
            ))

        return alerts

    async def check_project_deadlines(
        self,
        days_ahead: int = 14,
    ) -> List[TriggerAlert]:
        """檢查案件截止日"""
        from app.extended.models.core import ContractProject

        today = date.today()
        deadline_threshold = today + timedelta(days=days_ahead)
        alerts: List[TriggerAlert] = []

        # 已逾期案件（狀態仍為「執行中」）
        overdue_result = await self.db.execute(
            select(
                ContractProject.id,
                ContractProject.project_name,
                ContractProject.end_date,
                ContractProject.progress,
            )
            .where(
                ContractProject.end_date < today,
                ContractProject.end_date.isnot(None),
                ContractProject.status == "執行中",
            )
            .order_by(ContractProject.end_date)
            .limit(20)
        )
        for row in overdue_result.all():
            days_over = (today - row.end_date).days
            alerts.append(TriggerAlert(
                alert_type="deadline_overdue",
                severity="critical",
                title=f"案件已逾期 {days_over} 天",
                message=f"「{row.project_name}」已逾期 {days_over} 天，進度 {row.progress or 0}%",
                entity_type="project",
                entity_id=row.id,
                metadata={
                    "days_overdue": days_over,
                    "progress": row.progress,
                    "end_date": str(row.end_date),
                },
            ))

        # 即將到期案件
        upcoming_result = await self.db.execute(
            select(
                ContractProject.id,
                ContractProject.project_name,
                ContractProject.end_date,
                ContractProject.progress,
            )
            .where(
                ContractProject.end_date >= today,
                ContractProject.end_date <= deadline_threshold,
                ContractProject.end_date.isnot(None),
                ContractProject.status == "執行中",
            )
            .order_by(ContractProject.end_date)
            .limit(20)
        )
        for row in upcoming_result.all():
            days_left = (row.end_date - today).days
            alerts.append(TriggerAlert(
                alert_type="deadline_warning",
                severity="warning" if days_left <= 7 else "info",
                title=f"案件將於 {days_left} 天內到期",
                message=f"「{row.project_name}」將於 {row.end_date} 到期，進度 {row.progress or 0}%",
                entity_type="project",
                entity_id=row.id,
                metadata={
                    "days_remaining": days_left,
                    "progress": row.progress,
                    "end_date": str(row.end_date),
                },
            ))

        return alerts

    async def check_data_quality(self) -> List[TriggerAlert]:
        """檢查資料品質指標"""
        from app.extended.models.document import OfficialDocument

        alerts: List[TriggerAlert] = []

        # 檢查無主旨公文
        no_subject_result = await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                (OfficialDocument.subject.is_(None)) |
                (OfficialDocument.subject == "")
            )
        )
        no_subject_count = no_subject_result.scalar() or 0
        if no_subject_count > 0:
            alerts.append(TriggerAlert(
                alert_type="data_quality",
                severity="warning" if no_subject_count > 10 else "info",
                title=f"{no_subject_count} 筆公文缺少主旨",
                message=f"有 {no_subject_count} 筆公文沒有主旨，建議補充",
                entity_type="system",
                metadata={"count": no_subject_count},
            ))

        return alerts

    async def check_recommendations(self) -> List[TriggerAlert]:
        """檢查新公文是否匹配使用者興趣（主動推薦）"""
        alerts: List[TriggerAlert] = []
        try:
            from app.services.ai.proactive_recommender import ProactiveRecommender

            recommender = ProactiveRecommender(self.db)
            recs = await recommender.scan_recommendations(hours=24, min_score=2)

            # Group by user for summary alerts
            user_recs: Dict[str, list] = {}
            for rec in recs[:50]:
                uid = rec.get("user_id", "unknown")
                user_recs.setdefault(uid, []).append(rec)

            for uid, user_rec_list in user_recs.items():
                top = user_rec_list[0]
                alerts.append(TriggerAlert(
                    alert_type="recommendation",
                    severity="info",
                    title=f"{len(user_rec_list)} 筆新公文與使用者興趣相關",
                    message=(
                        f"使用者 {uid} 有 {len(user_rec_list)} 筆新公文推薦，"
                        f"最相關：「{top.get('subject', '')}」(分數 {top.get('score', 0)})"
                    ),
                    entity_type="document",
                    entity_id=top.get("document_id"),
                    metadata={
                        "user_id": uid,
                        "recommendation_count": len(user_rec_list),
                        "top_score": top.get("score", 0),
                    },
                ))
        except Exception as e:
            logger.debug("Recommendation check skipped: %s", e)

        return alerts

    async def check_unsummarized_documents(
        self,
        limit: int = 50,
    ) -> List[TriggerAlert]:
        """
        找出 NER 已完成但尚無 AI 摘要的公文，觸發摘要生成提醒。

        條件: ner_pending = false 且 document_ai_analyses 中無對應記錄
              (或記錄存在但 summary IS NULL)。
        """
        from app.extended.models.document import OfficialDocument
        from app.extended.models.ai_analysis import DocumentAIAnalysis

        alerts: List[TriggerAlert] = []

        # 子查詢：已有有效摘要的 document_id
        has_summary_subq = (
            select(DocumentAIAnalysis.document_id)
            .where(
                DocumentAIAnalysis.summary.isnot(None),
                DocumentAIAnalysis.status == "completed",
            )
        )

        result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
            )
            .where(
                OfficialDocument.ner_pending.is_(False),
                OfficialDocument.id.notin_(has_summary_subq),
            )
            .order_by(OfficialDocument.id.desc())
            .limit(limit)
        )
        rows = result.all()

        if rows:
            doc_ids = [r.id for r in rows]
            alerts.append(TriggerAlert(
                alert_type="unsummarized_documents",
                severity="info",
                title=f"{len(rows)} 筆公文已完成 NER 但尚無 AI 摘要",
                message=(
                    f"有 {len(rows)} 筆公文已完成實體提取，"
                    f"建議執行 AI 摘要生成以豐富知識庫"
                ),
                entity_type="system",
                metadata={
                    "count": len(rows),
                    "document_ids": doc_ids[:20],
                },
            ))

        return alerts

    async def get_alert_summary(self) -> Dict[str, Any]:
        """取得警報摘要（供 Dashboard 使用）"""
        alerts = await self.scan_all()

        by_severity = {"critical": 0, "warning": 0, "info": 0}
        by_type = {}

        for alert in alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1

        return {
            "total_alerts": len(alerts),
            "by_severity": by_severity,
            "by_type": by_type,
            "alerts": [
                {
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "metadata": a.metadata,
                }
                for a in alerts[:50]  # 最多 50 筆
            ],
        }
