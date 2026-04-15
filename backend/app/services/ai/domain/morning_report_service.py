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

        # 7. 待盤點資產
        sections["asset_pending_inventory"] = await self._get_asset_pending_inventory(
            today
        )

        # 8. 近期會議（CalendarEvent.event_type='meeting'，排除現勘關鍵字）
        sections["upcoming_meetings"] = await self._get_upcoming_meetings(
            today, week_later
        )

        # 9. 近期現勘（CalendarEvent 現勘關鍵字 + taoyuan work_records survey）
        sections["upcoming_site_visits"] = await self._get_upcoming_site_visits(
            today, week_later
        )

        return sections

    async def generate_summary(self) -> str:
        """Generate Gemma 4 natural language summary."""
        data = await self.generate_report()
        return await self.generate_summary_from_data(data)

    async def generate_summary_from_data(self, data: Dict[str, Any]) -> str:
        """Generate detailed summary with specific case information."""
        parts = []
        details = []  # 具體案件明細

        # 1. 本週到期派工 — 列出具體派工單
        dd = data.get("dispatch_deadlines", {})
        if dd.get("week_count", 0) > 0:
            parts.append(f"本週到期派工 {dd['week_count']} 筆")
            for item in dd.get("week_items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = "🔴 今日" if days == 0 else f"⏰ 剩 {days} 天"
                details.append(
                    f"  {urgency} {item['dispatch_no']} — "
                    f"{item.get('sub_case') or item.get('project_name', '')}"
                    f" (承辦: {item.get('handler', '未指定')}，到期: {item['deadline']})"
                )

        # 2. 逾期項目 — 列出具體派工單和公文
        ov = data.get("overdue_items", {})
        if ov.get("dispatch_count", 0) > 0:
            parts.append(f"逾期派工 {ov['dispatch_count']} 筆")
            for item in ov.get("dispatch_items", [])[:5]:
                details.append(
                    f"  🚨 逾期 {item['overdue_days']} 天 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                )
        if ov.get("doc_count", 0) > 0:
            parts.append(f"逾期公文 {ov['doc_count']} 筆")
            for item in ov.get("doc_items", [])[:3]:
                details.append(f"  📄 {item['doc_number']} — {item['subject']}")

        # 3. 待審費用 — 列出具體發票
        pe = data.get("pending_expenses", {})
        if pe.get("count", 0) > 0:
            parts.append(f"待審費用 {pe['count']} 筆 (NT${pe.get('total_amount', 0):,.0f})")
            for item in pe.get("items", [])[:3]:
                details.append(
                    f"  💰 {item.get('inv_num', '無號')} NT${item['amount']:,.0f} "
                    f"— {item.get('vendor', '')} ({item.get('case_code', '')})"
                )

        # 4. 里程碑 — 列出具體項目
        ms = data.get("upcoming_milestones", {})
        if ms.get("count", 0) > 0:
            parts.append(f"近期里程碑 {ms['count']} 項")
            for item in ms.get("items", [])[:3]:
                details.append(
                    f"  📌 {item['name']} — "
                    f"{item.get('case_name', '')} "
                    f"(到期: {item['due_date']})"
                )

        # 5. 新收公文
        nd = data.get("new_documents", {})
        if nd.get("count", 0) > 0:
            parts.append(f"昨日新收公文 {nd['count']} 筆")

        # 6. 標案
        ta = data.get("tender_alerts", {})
        if ta.get("count", 0) > 0:
            parts.append(f"標案訂閱 {ta['count']} 則")

        # 7. 待盤點資產
        ap = data.get("asset_pending_inventory", {})
        if ap.get("count", 0) > 0:
            parts.append(f"待盤點資產 {ap['count']} 項")

        # 8. 近期會議 — 列出具體場次
        mt = data.get("upcoming_meetings", {})
        if mt.get("count", 0) > 0:
            parts.append(f"近期會議 {mt['count']} 場")
            for item in mt.get("items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = (
                    "🔔 今日" if days == 0
                    else "📅 明日" if days == 1
                    else f"📅 {days} 天後"
                )
                time_str = item.get("time_str") or item.get("start_date", "")
                location = f" @ {item['location']}" if item.get("location") else ""
                details.append(
                    f"  {urgency} {time_str} {item['title'][:40]}{location}"
                )

        # 9. 近期現勘
        sv = data.get("upcoming_site_visits", {})
        if sv.get("count", 0) > 0:
            parts.append(f"近期現勘 {sv['count']} 場")
            for item in sv.get("items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = (
                    "🏗️ 今日" if days == 0
                    else "🏗️ 明日" if days == 1
                    else f"🏗️ {days} 天後"
                )
                time_str = item.get("time_str") or item.get("start_date", "")
                source = f" [{item['source']}]" if item.get("source") else ""
                location = f" @ {item['location']}" if item.get("location") else ""
                details.append(
                    f"  {urgency} {time_str} {item['title'][:40]}{location}{source}"
                )

        if not parts:
            return "📋 今日晨報：一切正常，無待處理事項。👍"

        # 組合：直接給明細，不需要 Gemma 4 (避免資訊遺失)
        header = f"📋 {datetime.now().strftime('%m/%d')} 晨報\n"
        summary_line = " | ".join(parts)
        detail_text = "\n".join(details) if details else ""

        report = f"{header}\n📊 {summary_line}\n"
        if detail_text:
            report += f"\n{detail_text}\n"

        # 用 Gemma 4 只生成一句結尾建議
        try:
            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            advice_prompt = (
                f"根據以下追蹤事項，給出一句簡短的今日工作建議（20字內）：\n"
                f"{summary_line}"
            )
            advice = await ai.chat_completion(
                messages=[{"role": "user", "content": advice_prompt}],
                temperature=0.5, max_tokens=50, task_type="chat",
            )
            report += f"\n💡 {advice.strip()}"
        except Exception:
            report += "\n💡 優先處理逾期和到期項目。"

        # 主動推薦: 整合 proactive_triggers 的今日建議行動
        try:
            from app.services.ai.proactive.proactive_triggers import ProactiveTriggerService
            trigger_svc = ProactiveTriggerService(self.db)
            alerts = await trigger_svc.scan_all(deadline_days=3)
            critical_alerts = [a for a in alerts if a.severity in ("critical", "warning")]
            if critical_alerts:
                report += "\n\n⚠️ 主動警報:\n"
                for alert in critical_alerts[:5]:
                    icon = "🔴" if alert.severity == "critical" else "🟡"
                    report += f"  {icon} {alert.title}: {alert.message}\n"
        except Exception:
            pass  # proactive triggers are non-critical

        return report

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
        """Get dispatch deadlines with DETAILS — not just counts."""
        try:
            r = await self.db.execute(
                text("""
                SELECT id, dispatch_no, deadline, project_name, case_handler, sub_case_name
                FROM taoyuan_dispatch_orders
                WHERE deadline IS NOT NULL AND deadline != '' AND batch_no IS NULL
            """)
            )
            today_items = []
            week_items = []
            for row in r.all():
                dl = self._parse_roc_date(row[2])
                if not dl:
                    continue
                item = {
                    "dispatch_no": row[1],
                    "deadline": str(dl),
                    "project_name": row[3] or "",
                    "handler": row[4] or "",
                    "sub_case": row[5] or "",
                    "days_left": (dl - today).days,
                }
                if dl == today:
                    today_items.append(item)
                if today <= dl <= week_later:
                    week_items.append(item)
            week_items.sort(key=lambda x: x["deadline"])
            return {
                "today_count": len(today_items),
                "week_count": len(week_items),
                "today_items": today_items,
                "week_items": week_items,
            }
        except Exception as e:
            logger.debug("dispatch_deadlines query failed: %s", e)
            return {"today_count": 0, "week_count": 0, "today_items": [], "week_items": []}

    async def _get_overdue_items(self, today) -> dict:
        """Get overdue items with DETAILS."""
        try:
            r1 = await self.db.execute(
                text("""
                SELECT id, dispatch_no, deadline, project_name, case_handler
                FROM taoyuan_dispatch_orders
                WHERE deadline IS NOT NULL AND deadline != '' AND batch_no IS NULL
            """)
            )
            overdue_dispatches = []
            for row in r1.all():
                dl = self._parse_roc_date(row[2])
                if dl and dl < today:
                    overdue_dispatches.append({
                        "dispatch_no": row[1],
                        "deadline": str(dl),
                        "project_name": row[3] or "",
                        "handler": row[4] or "",
                        "overdue_days": (today - dl).days,
                    })
            overdue_dispatches.sort(key=lambda x: -x["overdue_days"])

            r2 = await self.db.execute(
                text("""
                SELECT id, doc_number, subject, deadline
                FROM documents
                WHERE deadline IS NOT NULL AND deadline < :today AND status = 'pending'
                ORDER BY deadline
                LIMIT 10
            """),
                {"today": today},
            )
            overdue_docs = [
                {"doc_number": row[1], "subject": (row[2] or "")[:40], "deadline": str(row[3])}
                for row in r2.all()
            ]
            return {
                "dispatch_count": len(overdue_dispatches),
                "doc_count": len(overdue_docs),
                "dispatch_items": overdue_dispatches[:10],
                "doc_items": overdue_docs,
            }
        except Exception as e:
            logger.debug("overdue_items query failed: %s", e)
            return {"dispatch_count": 0, "doc_count": 0, "dispatch_items": [], "doc_items": []}

    async def _get_pending_expenses(self) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT id, inv_num, total_amount, status, case_code, vendor_name,
                       created_at
                FROM expense_invoices
                WHERE status IN ('pending', 'manager_approved')
                ORDER BY total_amount DESC
                LIMIT 10
            """)
            )
            items = []
            total_amount = 0.0
            for row in r.all():
                amt = float(row[2] or 0)
                total_amount += amt
                items.append({
                    "inv_num": row[1] or "",
                    "amount": amt,
                    "status": row[3],
                    "case_code": row[4] or "未歸屬",
                    "vendor": row[5] or "",
                })
            return {"count": len(items), "total_amount": total_amount, "items": items}
        except Exception as e:
            logger.debug("pending_expenses query failed: %s", e)
            return {"count": 0, "total_amount": 0, "items": []}

    async def _get_upcoming_milestones(self, today, week_later) -> dict:
        try:
            r = await self.db.execute(
                text("""
                SELECT m.id, m.milestone_name, m.due_date, m.status,
                       c.case_code, c.case_name
                FROM pm_milestones m
                LEFT JOIN pm_cases c ON c.id = m.pm_case_id
                WHERE m.due_date BETWEEN :today AND :week
                  AND m.status != 'completed'
                ORDER BY m.due_date
                LIMIT 5
            """),
                {"today": today, "week": week_later},
            )
            items = [
                {
                    "name": row[1] or "",
                    "due_date": str(row[2]),
                    "case_code": row[4] or "",
                    "case_name": row[5] or "",
                }
                for row in r.all()
            ]
            return {"count": len(items), "items": items}
        except Exception as e:
            logger.debug("upcoming_milestones query failed: %s", e)
            return {"count": 0, "items": []}

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

    async def _get_asset_pending_inventory(self, today) -> dict:
        """Get count of assets needing inventory (last inspected > 6 months ago or never)."""
        try:
            six_months_ago = today - timedelta(days=180)
            r = await self.db.execute(
                text("""
                SELECT COUNT(*) FROM assets
                WHERE last_inspect_date < :cutoff
                   OR last_inspect_date IS NULL
            """),
                {"cutoff": six_months_ago},
            )
            return {"count": r.scalar() or 0}
        except Exception as e:
            logger.debug("asset_pending_inventory query failed: %s", e)
            return {"count": 0}

    # 現勘關鍵字（從 title 判斷是否屬於現勘；會勘因常走現場，歸為現勘）
    _SITE_VISIT_KEYWORDS = ("會勘", "現勘", "勘查", "勘驗", "履勘", "現場勘查", "現場會勘")

    def _format_event_time(self, start_dt, all_day: bool) -> str:
        """格式化會議/現勘時間為可讀字串。"""
        if not start_dt:
            return ""
        if all_day:
            return start_dt.strftime("%m/%d") + " 全天"
        return start_dt.strftime("%m/%d %H:%M")

    def _is_site_visit(self, title: str) -> bool:
        return any(k in (title or "") for k in self._SITE_VISIT_KEYWORDS)

    async def _get_upcoming_meetings(self, today, week_later) -> dict:
        """近期會議（不含現勘），來源：document_calendar_events.event_type='meeting'"""
        try:
            r = await self.db.execute(
                text("""
                SELECT id, title, start_date, end_date, all_day, location, priority, status
                FROM document_calendar_events
                WHERE event_type = 'meeting'
                  AND status != 'cancelled'
                  AND DATE(start_date) BETWEEN :today AND :week
                ORDER BY start_date
                LIMIT 20
            """),
                {"today": today, "week": week_later},
            )
            items = []
            for row in r.all():
                title = row[1] or ""
                if self._is_site_visit(title):
                    continue  # 現勘另收
                start_dt = row[2]
                start_date = start_dt.date() if start_dt else None
                items.append({
                    "title": title,
                    "start_date": str(start_date) if start_date else "",
                    "time_str": self._format_event_time(start_dt, bool(row[4])),
                    "location": row[5] or "",
                    "priority": row[6] or "normal",
                    "days_left": (start_date - today).days if start_date else 0,
                })
            return {"count": len(items), "items": items}
        except Exception as e:
            logger.debug("upcoming_meetings query failed: %s", e)
            return {"count": 0, "items": []}

    async def _get_upcoming_site_visits(self, today, week_later) -> dict:
        """近期現勘：合併兩個來源
        1. document_calendar_events.event_type='meeting' 且 title 含現勘關鍵字
        2. taoyuan_work_records.work_category='survey_notice' 且 record_date 在未來範圍
        """
        items = []

        # Source 1: Calendar events
        try:
            r1 = await self.db.execute(
                text("""
                SELECT id, title, start_date, all_day, location, priority
                FROM document_calendar_events
                WHERE event_type = 'meeting'
                  AND status != 'cancelled'
                  AND DATE(start_date) BETWEEN :today AND :week
                ORDER BY start_date
                LIMIT 30
            """),
                {"today": today, "week": week_later},
            )
            for row in r1.all():
                title = row[1] or ""
                if not self._is_site_visit(title):
                    continue
                start_dt = row[2]
                start_date = start_dt.date() if start_dt else None
                items.append({
                    "title": title,
                    "start_date": str(start_date) if start_date else "",
                    "time_str": self._format_event_time(start_dt, bool(row[3])),
                    "location": row[4] or "",
                    "priority": row[5] or "normal",
                    "source": "calendar",
                    "days_left": (start_date - today).days if start_date else 0,
                })
        except Exception as e:
            logger.debug("site_visits calendar query failed: %s", e)

        # Source 2: Taoyuan work records (survey_notice)
        try:
            r2 = await self.db.execute(
                text("""
                SELECT wr.id, wr.description, wr.record_date, wr.milestone_type,
                       d.dispatch_no, d.project_name, d.sub_case_name
                FROM taoyuan_work_records wr
                LEFT JOIN taoyuan_dispatch_orders d ON d.id = wr.dispatch_order_id
                WHERE wr.work_category = 'survey_notice'
                  AND wr.status IN ('pending', 'in_progress')
                  AND wr.record_date BETWEEN :today AND :week
                ORDER BY wr.record_date
                LIMIT 20
            """),
                {"today": today, "week": week_later},
            )
            for row in r2.all():
                record_date = row[2]
                desc = row[1] or ""
                dispatch_no = row[4] or ""
                project = row[6] or row[5] or ""
                title = f"{dispatch_no} {project}".strip() or desc or "派工現勘"
                items.append({
                    "title": title[:60],
                    "start_date": str(record_date) if record_date else "",
                    "time_str": record_date.strftime("%m/%d") + " 現勘" if record_date else "",
                    "location": "",
                    "priority": "normal",
                    "source": "dispatch",
                    "days_left": (record_date - today).days if record_date else 0,
                })
        except Exception as e:
            logger.debug("site_visits dispatch query failed: %s", e)

        # 依 days_left 排序（近的先）
        items.sort(key=lambda x: x["days_left"])
        return {"count": len(items), "items": items}
