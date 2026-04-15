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
        """Generate daily morning report — 聚焦 4 主題：派工 / 會議 / 現勘 / 遺漏建檔。

        每段獨立呼叫 _safe_query；任一段查詢失敗即 rollback session，
        避免 PostgreSQL transaction abort 連帶讓後續查詢全數靜默失敗。
        """
        today = datetime.now().date()
        week_later = today + timedelta(days=7)

        sections: Dict[str, Any] = {}

        # 1. 派工：今日/本週到期 + 逾期
        sections["dispatch_deadlines"] = await self._safe_query(
            self._get_dispatch_deadlines, today, week_later,
            default={"today_count": 0, "week_count": 0, "today_items": [], "week_items": []},
        )
        sections["overdue_items"] = await self._safe_query(
            self._get_overdue_items, today,
            default={"dispatch_count": 0, "dispatch_items": []},
        )

        # 2. 會議（含 review 含會議字樣的補抓）
        sections["upcoming_meetings"] = await self._safe_query(
            self._get_upcoming_meetings, today, week_later,
            default={"count": 0, "items": []},
        )

        # 3. 現勘（calendar + 派工 work_records 雙來源）
        sections["upcoming_site_visits"] = await self._safe_query(
            self._get_upcoming_site_visits, today, week_later,
            default={"count": 0, "items": []},
        )

        # 4. 今日分桶 + 衝突（純函數，不需 safe wrapper）
        sections["today_schedule"] = self._compute_today_schedule(
            sections["upcoming_meetings"],
            sections["upcoming_site_visits"],
        )

        # 5. 遺漏建檔：開會/會勘通知單 14 天內未建 calendar event
        sections["missing_calendar_events"] = await self._safe_query(
            self._get_missing_calendar_events, today,
            default={"count": 0, "items": []},
        )

        return sections

    async def _safe_query(self, fn, *args, default):
        """執行查詢；失敗時 rollback session 並回 default，避免 transaction abort 擴散。"""
        try:
            return await fn(*args)
        except Exception as e:
            logger.warning("morning_report query failed (%s): %s", fn.__name__, e)
            try:
                await self.db.rollback()
            except Exception:
                pass
            return default

    async def generate_summary(self) -> str:
        """Generate Gemma 4 natural language summary."""
        data = await self.generate_report()
        return await self.generate_summary_from_data(data)

    async def generate_summary_from_data(self, data: Dict[str, Any]) -> str:
        """生成晨報摘要 — 聚焦 4 主題：派工 / 會議 / 現勘 / 遺漏建檔。"""
        parts = []
        details = []  # 具體案件明細

        # 1. 派工：本週到期
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

        # 2. 派工：逾期
        ov = data.get("overdue_items", {})
        if ov.get("dispatch_count", 0) > 0:
            parts.append(f"逾期派工 {ov['dispatch_count']} 筆")
            for item in ov.get("dispatch_items", [])[:5]:
                details.append(
                    f"  🚨 逾期 {item['overdue_days']} 天 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                )

        # 3. 會議
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

        # 10. 今日分桶 + 衝突
        ts = data.get("today_schedule", {})
        if ts.get("total", 0) > 0:
            morning = ts.get("morning", 0)
            afternoon = ts.get("afternoon", 0)
            evening = ts.get("evening", 0)
            time_of_day = []
            if morning:
                time_of_day.append(f"上午 {morning}")
            if afternoon:
                time_of_day.append(f"下午 {afternoon}")
            if evening:
                time_of_day.append(f"晚間 {evening}")
            parts.append(f"今日行程 {ts['total']} 場（{'/'.join(time_of_day) or '時段未定'}）")
            if ts.get("overload"):
                details.append(
                    f"  📛 今日 {ts['total']} 場行程超載（>=5），建議提前協調"
                )
            for conflict in ts.get("conflicts", [])[:3]:
                details.append(
                    f"  ⚠️ 衝突：{conflict['a_time']} {conflict['a_title'][:20]} "
                    f"與 {conflict['b_time']} {conflict['b_title'][:20]}"
                )

        # 11. 遺漏建檔
        mc = data.get("missing_calendar_events", {})
        if mc.get("count", 0) > 0:
            parts.append(f"⚠️ 公文未建行事曆 {mc['count']} 件")
            for item in mc.get("items", [])[:3]:
                details.append(
                    f"  📭 {item['doc_number']} {item['subject'][:35]}"
                    f"（{item['category']}，收文 {item['days_ago']} 天）"
                )

        if not parts:
            return f"📋 {datetime.now().strftime('%m/%d')} 晨報：今日無待處理派工/會議/現勘事項。👍"

        # 組合輸出（不依賴 LLM，避免資訊遺失與延遲）
        header = f"📋 {datetime.now().strftime('%m/%d')} 晨報\n"
        summary_line = " | ".join(parts)
        detail_text = "\n".join(details) if details else ""

        report = f"{header}\n📊 {summary_line}\n"
        if detail_text:
            report += f"\n{detail_text}\n"
        return report

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
        """到期派工（本週+今日）— 同樣排除「實質已完成」者，與逾期判定一致。"""
        try:
            r = await self.db.execute(
                text("""
                WITH closed_signals AS (
                  -- 訊號 A：work_records 有完成的成果/結案紀錄
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_work_records
                  WHERE work_category IN ('work_result', 'closed', 'submit_result')
                    AND status = 'completed'
                  UNION
                  -- 訊號 B：work_records 有對應公文的成果類紀錄（不需 status）
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_work_records
                  WHERE work_category IN ('work_result', 'submit_result')
                    AND document_id IS NOT NULL
                  UNION
                  -- 訊號 C：派工-公文鏈結有 company_outgoing（乾坤發文 = 已交付）
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_dispatch_document_link
                  WHERE link_type = 'company_outgoing'
                  UNION
                  -- 訊號 D：派工主表 company_doc_id 已填（舊欄位相容）
                  SELECT id AS dispatch_order_id
                  FROM taoyuan_dispatch_orders
                  WHERE company_doc_id IS NOT NULL
                )
                SELECT d.id, d.dispatch_no, d.deadline, d.project_name,
                       d.case_handler, d.sub_case_name
                FROM taoyuan_dispatch_orders d
                LEFT JOIN closed_signals c ON c.dispatch_order_id = d.id
                WHERE d.deadline IS NOT NULL
                  AND d.deadline != ''
                  AND d.batch_no IS NULL
                  AND c.dispatch_order_id IS NULL
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
        """逾期判定（雙條件）：

        一張派工視為「實質已完成」並排除在逾期之外，須符合任一：
        - 主表 batch_no IS NOT NULL（最終結案批次已建立）
        - work_records 鏈上有 work_category IN
          ('work_result','closed','submit_result') 且 status='completed'
          （已交付 / 已結案 / 已提送成果）

        僅當「未結案 + deadline < today」才列入逾期。
        對應派工單 001 案例：batch_no=NULL 但有 work_result completed → 排除。
        """
        try:
            r1 = await self.db.execute(
                text("""
                WITH closed_signals AS (
                  -- 訊號 A：work_records 有完成的成果/結案紀錄
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_work_records
                  WHERE work_category IN ('work_result', 'closed', 'submit_result')
                    AND status = 'completed'
                  UNION
                  -- 訊號 B：work_records 有對應公文的成果類紀錄（不需 status）
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_work_records
                  WHERE work_category IN ('work_result', 'submit_result')
                    AND document_id IS NOT NULL
                  UNION
                  -- 訊號 C：派工-公文鏈結有 company_outgoing（乾坤發文 = 已交付）
                  SELECT DISTINCT dispatch_order_id
                  FROM taoyuan_dispatch_document_link
                  WHERE link_type = 'company_outgoing'
                  UNION
                  -- 訊號 D：派工主表 company_doc_id 已填（舊欄位相容）
                  SELECT id AS dispatch_order_id
                  FROM taoyuan_dispatch_orders
                  WHERE company_doc_id IS NOT NULL
                )
                SELECT d.id, d.dispatch_no, d.deadline, d.project_name, d.case_handler
                FROM taoyuan_dispatch_orders d
                LEFT JOIN closed_signals c ON c.dispatch_order_id = d.id
                WHERE d.deadline IS NOT NULL
                  AND d.deadline != ''
                  AND d.batch_no IS NULL
                  AND c.dispatch_order_id IS NULL
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

            return {
                "dispatch_count": len(overdue_dispatches),
                "dispatch_items": overdue_dispatches[:10],
            }
        except Exception:
            raise  # 由 _safe_query 統一處理 rollback

    # 現勘關鍵字（從 title 判斷是否屬於現勘；會勘因常走現場，歸為現勘）
    _SITE_VISIT_KEYWORDS = ("會勘", "現勘", "勘查", "勘驗", "履勘", "現場勘查", "現場會勘")

    # 遺漏建檔偵測：這些公文類別應主動建行事曆事件
    _DOC_CATEGORIES_REQUIRE_EVENT = ("開會通知單", "會勘通知單", "會議通知單")

    def _compute_today_schedule(self, meetings: dict, site_visits: dict) -> dict:
        """合併今日會議 + 現勘，分桶（上午/下午/晚間）+ 衝突偵測。

        衝突定義：兩事件開始時間差 < 30 分鐘視為潛在衝突。
        超載警示：今日總場次 >= 5。
        """
        today_items = []
        for src_name, src in (("meeting", meetings), ("site_visit", site_visits)):
            for item in src.get("items", []):
                if item.get("days_left") != 0:
                    continue
                time_str = item.get("time_str") or ""
                # 從 time_str 提取 HH:MM（格式：04/16 14:30 或 04/16 現勘）
                hour = None
                minute = 0
                import re
                m = re.search(r"(\d{2}):(\d{2})", time_str)
                if m:
                    hour = int(m.group(1))
                    minute = int(m.group(2))
                today_items.append({
                    "kind": src_name,
                    "title": item.get("title", ""),
                    "time_str": time_str,
                    "hour": hour,
                    "minute": minute,
                    "location": item.get("location", ""),
                })

        morning = sum(1 for x in today_items if x["hour"] is not None and x["hour"] < 12)
        afternoon = sum(
            1 for x in today_items
            if x["hour"] is not None and 12 <= x["hour"] < 18
        )
        evening = sum(1 for x in today_items if x["hour"] is not None and x["hour"] >= 18)

        # 衝突偵測（只看有明確時間的）
        scheduled = [x for x in today_items if x["hour"] is not None]
        scheduled.sort(key=lambda x: x["hour"] * 60 + x["minute"])
        conflicts = []
        for i in range(len(scheduled) - 1):
            a = scheduled[i]
            b = scheduled[i + 1]
            a_min = a["hour"] * 60 + a["minute"]
            b_min = b["hour"] * 60 + b["minute"]
            if b_min - a_min < 30:
                conflicts.append({
                    "a_title": a["title"],
                    "a_time": a["time_str"],
                    "b_title": b["title"],
                    "b_time": b["time_str"],
                    "gap_minutes": b_min - a_min,
                })

        total = len(today_items)
        return {
            "total": total,
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "overload": total >= 5,
            "conflicts": conflicts,
            "items": today_items,
        }

    async def _get_missing_calendar_events(self, today) -> dict:
        """偵測近 14 天開會/會勘通知單但未建 calendar event 的公文。"""
        try:
            cutoff = today - timedelta(days=14)
            # category 可能為全名或縮寫，以 LIKE 寬鬆比對
            r = await self.db.execute(
                text("""
                SELECT d.id, d.doc_number, d.subject, d.category, d.receive_date,
                       d.created_at
                FROM documents d
                LEFT JOIN document_calendar_events e ON e.document_id = d.id
                WHERE d.category IN ('開會通知單', '會勘通知單', '會議通知單')
                  AND d.created_at::date >= :cutoff
                  AND e.id IS NULL
                ORDER BY d.created_at DESC
                LIMIT 10
            """),
                {"cutoff": cutoff},
            )
            items = []
            for row in r.all():
                created = row[5]
                days_ago = (today - created.date()).days if created else 0
                items.append({
                    "doc_number": row[1] or "",
                    "subject": (row[2] or "")[:60],
                    "category": row[3] or "",
                    "receive_date": str(row[4]) if row[4] else "",
                    "days_ago": days_ago,
                })
            return {"count": len(items), "items": items}
        except Exception as e:
            logger.debug("missing_calendar_events query failed: %s", e)
            return {"count": 0, "items": []}

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
        """近期會議（不含現勘）。

        擴大涵蓋 event_type IN ('meeting', 'review')，避免「審查會議」被歸到
        review 而漏掉（CalendarEventAutoBuilder KEYWORD 規則順序：審查 > 會議）。
        review 類別需 title 含會議/開會字樣才納入；純「[審查]」公文不算。
        """
        try:
            r = await self.db.execute(
                text("""
                SELECT id, title, start_date, end_date, all_day, location, priority, status, event_type
                FROM document_calendar_events
                WHERE status != 'cancelled'
                  AND DATE(start_date) BETWEEN :today AND :week
                  AND (
                    event_type = 'meeting'
                    OR (event_type = 'review' AND (
                        title LIKE '%會議%' OR title LIKE '%開會%' OR title LIKE '%協商%'
                    ))
                  )
                ORDER BY start_date
                LIMIT 30
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
        # 同樣放寬 event_type 涵蓋 meeting + review，由 _is_site_visit 二次過濾
        try:
            r1 = await self.db.execute(
                text("""
                SELECT id, title, start_date, all_day, location, priority
                FROM document_calendar_events
                WHERE event_type IN ('meeting', 'review')
                  AND status != 'cancelled'
                  AND DATE(start_date) BETWEEN :today AND :week
                ORDER BY start_date
                LIMIT 50
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
