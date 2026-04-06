"""Morning Report Service — 每日晨報自動生成 + 推送

每日早上 8:00 自動彙整：
1. 今日到期派工單
2. 逾期未結案項目
3. 待審核費用
4. 近期里程碑
5. 新收公文
6. 標案訂閱通知

透過 Gemma 4 合成自然語言摘要，推送到 Telegram/LINE。
不依賴 OpenClaw — 後端 APScheduler 直接觸發。

Version: 1.0.0
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MorningReportService:
    """Generate and push daily morning reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self) -> Dict[str, Any]:
        """Generate daily morning report data."""
        today = datetime.now().date()
        week_later = today + timedelta(days=7)

        sections: Dict[str, Any] = {}

        # 1. 今日/本週到期派工
        sections["dispatch_deadlines"] = await self._get_dispatch_deadlines(
            today, week_later
        )

        # 2. 逾期未結案
        sections["overdue_items"] = await self._get_overdue_items(today)

        # 3. 待審核費用
        sections["pending_expenses"] = await self._get_pending_expenses()

        # 4. 近期里程碑
        sections["upcoming_milestones"] = await self._get_upcoming_milestones(
            today, week_later
        )

        # 5. 昨日新收公文
        sections["new_documents"] = await self._get_new_documents(
            today - timedelta(days=1)
        )

        # 6. 標案訂閱
        sections["tender_alerts"] = await self._get_tender_alerts()

        return sections

    async def generate_summary(self) -> str:
        """Generate Gemma 4 natural language summary."""
        data = await self.generate_report()
        return await self.generate_summary_from_data(data)

    async def generate_summary_from_data(self, data: Dict[str, Any]) -> str:
        """Generate Gemma 4 summary from pre-fetched report data."""
        # Build data summary for Gemma 4
        parts = []
        dd = data.get("dispatch_deadlines", {})
        if dd.get("today_count", 0) > 0:
            parts.append(f"今日到期派工 {dd['today_count']} 筆")
        if dd.get("week_count", 0) > 0:
            parts.append(f"本週到期 {dd['week_count']} 筆")

        ov = data.get("overdue_items", {})
        if ov.get("dispatch_count", 0) > 0:
            parts.append(f"逾期派工 {ov['dispatch_count']} 筆")
        if ov.get("doc_count", 0) > 0:
            parts.append(f"逾期公文 {ov['doc_count']} 筆")

        pe = data.get("pending_expenses", {})
        if pe.get("count", 0) > 0:
            parts.append(
                f"待審費用 {pe['count']} 筆 (${pe.get('total_amount', 0):,.0f})"
            )

        ms = data.get("upcoming_milestones", {})
        if ms.get("count", 0) > 0:
            parts.append(f"近期里程碑 {ms['count']} 項")

        nd = data.get("new_documents", {})
        if nd.get("count", 0) > 0:
            parts.append(f"昨日新收公文 {nd['count']} 筆")

        ta = data.get("tender_alerts", {})
        if ta.get("count", 0) > 0:
            parts.append(f"標案提醒 {ta['count']} 則")

        if not parts:
            return "📋 今日晨報：一切正常，無待處理事項。"

        # Gemma 4 summarize
        try:
            from app.core.ai_connector import get_ai_connector

            ai = get_ai_connector()
            data_text = "\n".join(f"- {p}" for p in parts)
            prompt = (
                f"你是乾坤測繪的 AI 助理。根據以下今日摘要生成簡潔晨報：\n\n"
                f"日期: {datetime.now().strftime('%Y-%m-%d %A')}\n"
                f"追蹤事項:\n{data_text}\n\n"
                "要求:\n"
                "- 用 emoji 開頭每個項目\n"
                "- 重要/緊急的放前面\n"
                "- 結尾給一句鼓勵\n"
                "- 控制在 500 字內"
            )
            summary = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=600,
                task_type="summary",
            )
            return f"📋 {datetime.now().strftime('%m/%d')} 晨報\n\n{summary}"
        except Exception as e:
            logger.warning("Gemma 4 summary failed: %s", e)
            # Fallback: plain format
            header = f"📋 {datetime.now().strftime('%m/%d')} 晨報\n"
            return header + "\n".join(f"• {p}" for p in parts)

    # ── Data Collection Methods ──

    @staticmethod
    def _parse_roc_date(s: str):
        """Parse ROC date string like '115年01月15日' to datetime.date."""
        import re
        m = re.match(r'(\d{2,3})\D+(\d{1,2})\D+(\d{1,2})', s or '')
        if m:
            try:
                from datetime import date as _date
                return _date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
            except (ValueError, TypeError):
                pass
        return None

    async def _get_dispatch_deadlines(self, today, week_later) -> dict:
        """Count dispatch deadlines — handles ROC date format (varchar)."""
        try:
            r = await self.db.execute(
                text("""
                SELECT id, deadline FROM taoyuan_dispatch_orders
                WHERE deadline IS NOT NULL AND deadline != '' AND batch_no IS NULL
            """)
            )
            today_count = 0
            week_count = 0
            for row in r.all():
                dl = self._parse_roc_date(row[1])
                if not dl:
                    continue
                if dl == today:
                    today_count += 1
                if today <= dl <= week_later:
                    week_count += 1
            return {"today_count": today_count, "week_count": week_count}
        except Exception as e:
            logger.debug("dispatch_deadlines query failed: %s", e)
            return {"today_count": 0, "week_count": 0}

    async def _get_overdue_items(self, today) -> dict:
        """Count overdue items — handles ROC date for dispatch, Date for documents."""
        try:
            # Dispatch: ROC date varchar
            r1 = await self.db.execute(
                text("""
                SELECT deadline FROM taoyuan_dispatch_orders
                WHERE deadline IS NOT NULL AND deadline != '' AND batch_no IS NULL
            """)
            )
            dispatch_overdue = 0
            for row in r1.all():
                dl = self._parse_roc_date(row[0])
                if dl and dl < today:
                    dispatch_overdue += 1

            # Documents: proper date field
            r2 = await self.db.execute(
                text("""
                SELECT COUNT(*) FROM documents
                WHERE deadline IS NOT NULL AND deadline < :today AND status = 'pending'
            """),
                {"today": today},
            )
            return {
                "dispatch_count": dispatch_overdue,
                "doc_count": r2.scalar() or 0,
            }
        except Exception as e:
            logger.debug("overdue_items query failed: %s", e)
            return {"dispatch_count": 0, "doc_count": 0}

    async def _get_pending_expenses(self) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
                FROM expense_invoices
                WHERE status IN ('pending', 'manager_approved')
            """)
            )
            row = r.first()
            return {
                "count": row[0] or 0 if row else 0,
                "total_amount": float(row[1] or 0) if row else 0,
            }
        except Exception as e:
            logger.debug("pending_expenses query failed: %s", e)
            return {"count": 0, "total_amount": 0}

    async def _get_upcoming_milestones(self, today, week_later) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT COUNT(*) FROM pm_milestones
                WHERE due_date BETWEEN :today AND :week
                  AND status != 'completed'
            """),
                {"today": today, "week": week_later},
            )
            return {"count": r.scalar() or 0}
        except Exception as e:
            logger.debug("upcoming_milestones query failed: %s", e)
            return {"count": 0}

    async def _get_new_documents(self, since) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT COUNT(*) FROM documents
                WHERE created_at::date >= :since
            """),
                {"since": since},
            )
            return {"count": r.scalar() or 0}
        except Exception as e:
            logger.debug("new_documents query failed: %s", e)
            return {"count": 0}

    async def _get_tender_alerts(self) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT COUNT(*) FROM tender_subscriptions
                WHERE is_active = true
            """)
            )
            return {"count": r.scalar() or 0}
        except Exception as e:
            logger.debug("tender_alerts query failed: %s", e)
            return {"count": 0}
