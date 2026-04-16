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
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

# A3: 顯式時區，避免 server TZ 漂移導致日期邊界錯誤
TZ_TAIPEI = ZoneInfo("Asia/Taipei")


def _now_taipei() -> datetime:
    """統一取得 Asia/Taipei 當前時間。"""
    return datetime.now(TZ_TAIPEI)


class MorningReportService:
    """Generate and push daily morning reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self) -> Dict[str, Any]:
        """Generate daily morning report — 聚焦 4 主題：派工 / 會議 / 現勘 / 遺漏建檔。

        每段獨立呼叫 _safe_query；任一段查詢失敗即 rollback session，
        避免 PostgreSQL transaction abort 連帶讓後續查詢全數靜默失敗。
        """
        today = _now_taipei().date()
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

        # 6. PM 逾期里程碑（B2 optional section，預設收集但僅訂閱者看到）
        sections["pm_overdue_milestones"] = await self._safe_query(
            self._get_pm_overdue_milestones, today,
            default={"count": 0, "items": []},
        )

        # 7. ERP 待審費用（B2 optional section）
        sections["erp_pending_expenses"] = await self._safe_query(
            self._get_erp_pending_expenses,
            default={"count": 0, "total_amount": 0, "items": []},
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

    async def generate_summary_from_data(
        self,
        data: Dict[str, Any],
        sections: set[str] | None = None,
    ) -> str:
        """生成晨報摘要 — 聚焦 4 主題：派工 / 會議 / 現勘 / 遺漏建檔。

        B2: sections 參數限定渲染範圍；None 保留既有行為（4 主題 default）。
        可選 key: dispatch, meeting, site_visit, missing, pm_milestone, erp_expense, all
        """
        allowed = sections
        if allowed is None:
            allowed = {"dispatch", "meeting", "site_visit", "missing"}
        elif "all" in allowed:
            allowed = {
                "dispatch", "meeting", "site_visit", "missing",
                "pm_milestone", "erp_expense",
            }

        def _on(key: str) -> bool:
            return key in allowed

        parts = []
        details = []  # 具體案件明細

        # 1. 派工：本週到期
        dd = data.get("dispatch_deadlines", {}) if _on("dispatch") else {}
        if dd.get("week_count", 0) > 0:
            parts.append(f"本週到期派工 {dd['week_count']} 筆")
            for item in dd.get("week_items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = "🔴 今日" if days == 0 else f"⏰ 剩 {days} 天"
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                details.append(
                    f"  {urgency} {item['dispatch_no']} — "
                    f"{item.get('sub_case') or item.get('project_name', '')}"
                    f" (承辦: {item.get('handler', '未指定')}，到期: {item['deadline']})"
                    f"{progress_tag}"
                )

        # 2a. 派工：真正逾期（active 狀態 + 超過期限）
        ov = data.get("overdue_items", {}) if _on("dispatch") else {}
        if ov.get("dispatch_count", 0) > 0:
            parts.append(f"逾期派工 {ov['dispatch_count']} 筆")
            for item in ov.get("dispatch_items", [])[:5]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                details.append(
                    f"  🚨 逾期 {item['overdue_days']} 天 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}"
                )

        # 2b. 派工：待結案確認（L3 — 全部完成但未發文）
        pc = ov.get("pending_closure_count", 0) if _on("dispatch") else 0
        if pc > 0:
            parts.append(f"待結案確認 {pc} 筆")
            for item in ov.get("pending_closure_items", [])[:3]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                details.append(
                    f"  📋 待結案 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}"
                )

        # 3. 會議（header 第二位）
        mt = data.get("upcoming_meetings", {}) if _on("meeting") else {}
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
                    f"  {urgency} {time_str} {item['title']}{location}"
                )

        # 9. 近期現勘
        sv = data.get("upcoming_site_visits", {}) if _on("site_visit") else {}
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
                    f"  {urgency} {time_str} {item['title']}{location}{source}"
                )

        # 2d. 排程作業（有未來行事曆事件，非停滯逾期）— header 第三位
        sc = ov.get("scheduled_count", 0) if _on("dispatch") else 0
        if sc > 0:
            parts.append(f"排程作業 {sc} 筆")
            for item in ov.get("scheduled_items", [])[:3]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                next_ev = item.get("next_event", "")
                next_tag = f" → 下次 {next_ev}" if next_ev else ""
                details.append(
                    f"  📅 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}{next_tag}"
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
                    f"  ⚠️ 衝突：{conflict['a_time']} {conflict['a_title']} "
                    f"與 {conflict['b_time']} {conflict['b_title']}"
                )

        # 11. 遺漏建檔
        mc = data.get("missing_calendar_events", {}) if _on("missing") else {}
        if mc.get("count", 0) > 0:
            parts.append(f"⚠️ 公文未建行事曆 {mc['count']} 件")
            for item in mc.get("items", [])[:3]:
                details.append(
                    f"  📭 {item['doc_number']} {item['subject']}"
                    f"（{item['category']}，收文 {item['days_ago']} 天）"
                )

        # 12. PM 逾期里程碑（B2 optional）
        if _on("pm_milestone"):
            pm = data.get("pm_overdue_milestones", {}) or {}
            if pm.get("count", 0) > 0:
                parts.append(f"PM 逾期里程碑 {pm['count']} 項")
                for item in pm.get("items", [])[:5]:
                    details.append(
                        f"  🏁 逾期 {item['overdue_days']} 天 {item['case_code']} "
                        f"{item['milestone_name']}（{item['status']}）"
                    )

        # 13. ERP 待審費用（B2 optional）— >3 天 pending
        if _on("erp_expense"):
            ex = data.get("erp_pending_expenses", {}) or {}
            if ex.get("count", 0) > 0:
                total = ex.get("total_amount", 0)
                parts.append(
                    f"ERP 待審費用 {ex['count']} 筆 "
                    f"(合計 NT$ {int(total):,})"
                )
                for item in ex.get("items", [])[:3]:
                    details.append(
                        f"  💰 {item['inv_num']} NT$ {int(item['amount']):,} "
                        f"〔{item['status']}〕{item['uploader']}"
                    )

        if not parts:
            return f"📋 {_now_taipei().strftime('%m/%d')} 晨報：今日無待處理派工/會議/現勘事項。👍"

        # 組合輸出（不依賴 LLM，避免資訊遺失與延遲）
        header = f"📋 {_now_taipei().strftime('%m/%d')} 晨報\n"
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

    # A4+L2L3: 共用 CTE — 聚合完成比例 + doc_links + 行事曆排程 + 結案判定
    #
    # closure_level 分層：
    #   'closed'          — L1: milestone=closed/final_approval 且 completed
    #   'delivered'       — L2: 100% completed + has work_result + has_out（成果已交付）
    #   'all_completed'   — L2b: 100% completed + has_out（全部完成+已發文）
    #   'pending_closure' — L3: 100% completed（完成但未發文）
    #   'scheduled'       — 未全部完成但有未來行事曆事件（有排程，非停滯）
    #   'active'          — 進行中且無排程 → 真正逾期/到期
    #
    # 設計依據：用戶指示「以作業進度 + 公文對照其狀態期限為基準，非 batch_no」。
    # 有排程的 dispatch 不算逾期，應以行事曆事件時間為下次行動基準。
    _ACTIVE_DISPATCHES_SQL = """
        WITH record_progress AS (
          SELECT dispatch_order_id,
                 COUNT(*) AS total_records,
                 COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
                 BOOL_OR(work_category = 'work_result' AND status = 'completed') AS has_work_result_completed,
                 BOOL_OR(milestone_type IN ('closed', 'final_approval') AND status = 'completed') AS has_formal_closure
          FROM taoyuan_work_records
          WHERE dispatch_order_id IS NOT NULL
          GROUP BY dispatch_order_id
        ),
        latest_record AS (
          SELECT DISTINCT ON (dispatch_order_id)
            dispatch_order_id, milestone_type, work_category, status
          FROM taoyuan_work_records
          WHERE dispatch_order_id IS NOT NULL
          ORDER BY dispatch_order_id, record_date DESC, id DESC
        ),
        doc_links AS (
          SELECT dispatch_order_id,
                 BOOL_OR(link_type = 'agency_incoming') AS has_in,
                 BOOL_OR(link_type = 'company_outgoing') AS has_out
          FROM taoyuan_dispatch_document_link
          GROUP BY dispatch_order_id
        ),
        upcoming_events AS (
          SELECT ddl.dispatch_order_id,
                 MIN(ce.start_date) AS next_event_date,
                 COUNT(*) AS upcoming_count
          FROM taoyuan_dispatch_document_link ddl
          JOIN documents doc ON doc.id = ddl.document_id
          JOIN document_calendar_events ce ON ce.document_id = doc.id
          WHERE ce.start_date >= CURRENT_DATE
            AND ce.status != 'cancelled'
          GROUP BY ddl.dispatch_order_id
        )
        SELECT d.id, d.dispatch_no, d.deadline, d.project_name,
               d.case_handler, d.sub_case_name,
               l.milestone_type, l.work_category, l.status,
               COALESCE(dl.has_in, false) AS has_in,
               COALESCE(dl.has_out, false) AS has_out,
               CASE
                 WHEN COALESCE(rp.has_formal_closure, false)
                   THEN 'closed'
                 WHEN rp.total_records > 0
                      AND rp.completed_count = rp.total_records
                      AND COALESCE(rp.has_work_result_completed, false)
                      AND COALESCE(dl.has_out, false) = true
                   THEN 'delivered'
                 WHEN rp.total_records > 0
                      AND rp.completed_count = rp.total_records
                      AND COALESCE(dl.has_out, false) = true
                   THEN 'all_completed'
                 WHEN rp.total_records > 0
                      AND rp.completed_count = rp.total_records
                   THEN 'pending_closure'
                 WHEN ue.upcoming_count > 0
                   THEN 'scheduled'
                 ELSE 'active'
               END AS closure_level,
               COALESCE(rp.completed_count, 0) AS completed_count,
               COALESCE(rp.total_records, 0) AS total_records,
               ue.next_event_date
        FROM taoyuan_dispatch_orders d
        LEFT JOIN record_progress rp ON rp.dispatch_order_id = d.id
        LEFT JOIN latest_record l ON l.dispatch_order_id = d.id
        LEFT JOIN doc_links dl ON dl.dispatch_order_id = d.id
        LEFT JOIN upcoming_events ue ON ue.dispatch_order_id = d.id
        WHERE d.deadline IS NOT NULL
          AND d.deadline != ''
    """

    async def _get_dispatch_deadlines(self, today, week_later) -> dict:
        """到期派工（本週+今日）— 以作業進度 + 公文對照為基準。

        三層結案判定（closure_level）：
        - closed / delivered → 完全排除（L1+L2，系統結案或成果已交付）
        - pending_closure → 排除到期清單（已實質完成，僅差補結案）
        - active → 列入，標註作業進度標籤
        """
        try:
            r = await self.db.execute(text(self._ACTIVE_DISPATCHES_SQL))
            today_items = []
            week_items = []
            for row in r.all():
                closure = row[11]  # closure_level
                if closure in ("closed", "delivered", "all_completed",
                              "pending_closure", "scheduled"):
                    continue  # 到期清單不含已完成/有排程項目
                dl = self._parse_roc_date(row[2])
                if not dl:
                    continue
                completed_n, total_n = row[12], row[13]
                progress_bar = f" ({completed_n}/{total_n})" if total_n else ""
                item = {
                    "dispatch_no": row[1],
                    "deadline": str(dl),
                    "project_name": row[3] or "",
                    "handler": row[4] or "",
                    "sub_case": row[5] or "",
                    "days_left": (dl - today).days,
                    "progress": self._format_dispatch_progress(
                        row[6], row[7], row[8], row[9], row[10]
                    ) + progress_bar,
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
        except Exception:
            raise

    @staticmethod
    def _format_dispatch_progress(
        milestone_type, work_category, status, has_in, has_out
    ) -> str:
        """組合派工當前作業進度標籤。

        例：「成果已交付/已對應發文」「現勘進行中/僅有來文」「無作業紀錄」
        """
        # 階段判定：以最新 record 的 milestone/category 為準
        stage_map = {
            "closed": "已結案",
            "final_approval": "最終驗收完成",
            "submit_result": "提送成果",
            "review_meeting": "審查會議",
            "negotiation": "協商中",
            "boundary_survey": "界址測量",
            "survey": "查估",
            "revision": "修正中",
            "dispatch": "派工通知",
        }
        cat_map = {
            "admin_notice": "行政通知",
            "dispatch_notice": "派工通知",
            "work_result": "成果回函",
            "meeting_notice": "會議通知",
            "meeting_record": "會議紀錄",
            "survey_notice": "現勘通知",
            "survey_record": "現勘紀錄",
        }
        status_map = {
            "completed": "完成", "in_progress": "進行中",
            "pending": "待辦", "overdue": "逾期", "on_hold": "暫緩",
        }

        if milestone_type or work_category:
            stage = stage_map.get(milestone_type) or cat_map.get(work_category) or "處理中"
            st = status_map.get(status, status or "")
            stage_str = f"{stage} {st}" if st else stage
        else:
            stage_str = "無作業紀錄"

        # 公文對照狀態
        if has_out:
            doc_str = "已對應發文"
        elif has_in:
            doc_str = "僅有來文"
        else:
            doc_str = "無公文對照"

        return f"{stage_str} / {doc_str}"

    async def _get_overdue_items(self, today) -> dict:
        """逾期判定（同到期邏輯）：

        以「作業進度 + 公文對照狀態期限」為基準（不依賴 batch_no）。
        三層結案判定：
        - L1 closed/L2 delivered → 完全排除
        - L3 pending_closure → 拆到 pending_closure_items（待結案確認）
        - active → 真正逾期
        """
        try:
            r1 = await self.db.execute(text(self._ACTIVE_DISPATCHES_SQL))
            overdue_dispatches = []
            pending_closure = []
            scheduled_items = []
            for row in r1.all():
                dl = self._parse_roc_date(row[2])
                if not dl or dl >= today:
                    continue
                closure = row[11]  # closure_level
                if closure in ("closed", "delivered", "all_completed"):
                    continue  # L1+L2+L2b: 完全排除
                completed_n, total_n = row[12], row[13]
                next_event = row[14]  # next_event_date or None
                progress_bar = f" ({completed_n}/{total_n})" if total_n else ""
                item = {
                    "dispatch_no": row[1],
                    "deadline": str(dl),
                    "progress": self._format_dispatch_progress(
                        row[6], row[7], row[8], row[9], row[10]
                    ) + progress_bar,
                    "project_name": row[3] or "",
                    "handler": row[4] or "",
                    "overdue_days": (today - dl).days,
                    "next_event": str(next_event.date()) if hasattr(next_event, 'date') else str(next_event) if next_event else None,
                }
                if closure == "pending_closure":
                    pending_closure.append(item)
                elif closure == "scheduled":
                    scheduled_items.append(item)
                else:
                    overdue_dispatches.append(item)  # active: 真正逾期
            overdue_dispatches.sort(key=lambda x: -x["overdue_days"])
            pending_closure.sort(key=lambda x: -x["overdue_days"])
            scheduled_items.sort(key=lambda x: x.get("next_event") or "")

            return {
                "dispatch_count": len(overdue_dispatches),
                "dispatch_items": overdue_dispatches[:10],
                "pending_closure_count": len(pending_closure),
                "pending_closure_items": pending_closure[:10],
                "scheduled_count": len(scheduled_items),
                "scheduled_items": scheduled_items[:10],
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

    # B2: PM 逾期里程碑 — 非預設主題，由訂閱開關
    async def _get_pm_overdue_milestones(self, today) -> dict:
        """PM 里程碑逾期：planned_date < today 且 status 非 completed/skipped。"""
        try:
            r = await self.db.execute(
                text("""
                SELECT m.id, m.milestone_name, m.planned_date, m.status,
                       c.case_code, c.case_name
                FROM pm_milestones m
                JOIN pm_cases c ON c.id = m.pm_case_id
                WHERE m.planned_date IS NOT NULL
                  AND m.planned_date < :today
                  AND m.status NOT IN ('completed', 'skipped')
                ORDER BY m.planned_date ASC
                LIMIT 10
            """),
                {"today": today},
            )
            items = []
            for row in r.all():
                pd = row[2]
                items.append({
                    "milestone_name": row[1] or "",
                    "planned_date": str(pd) if pd else "",
                    "status": row[3] or "",
                    "case_code": row[4] or "",
                    "case_name": row[5] or "",
                    "overdue_days": (today - pd).days if pd else 0,
                })
            return {"count": len(items), "items": items}
        except Exception:
            raise

    # B2: ERP 待審費用 — 非預設主題，由訂閱開關
    async def _get_erp_pending_expenses(self) -> dict:
        """ERP 費用報銷處於 pending 狀態 > 3 天者，彙總金額 + 前 10 筆明細。"""
        try:
            r = await self.db.execute(
                text("""
                SELECT e.id, e.inv_num, e.amount, e.date, e.category, e.status,
                       u.full_name
                FROM expense_invoices e
                LEFT JOIN users u ON u.id = e.user_id
                WHERE e.status IN ('pending', 'pending_receipt', 'manager_approved')
                  AND e.created_at < NOW() - INTERVAL '3 days'
                ORDER BY e.created_at ASC
                LIMIT 10
            """)
            )
            items = []
            total = 0
            for row in r.all():
                amt = float(row[2] or 0)
                total += amt
                items.append({
                    "inv_num": row[1] or "",
                    "amount": amt,
                    "date": str(row[3]) if row[3] else "",
                    "category": row[4] or "",
                    "status": row[5] or "",
                    "uploader": row[6] or "未知",
                })
            # 再補上 total 實際全量（不受 LIMIT 影響）
            r2 = await self.db.execute(
                text("""
                SELECT COUNT(*), COALESCE(SUM(amount), 0)
                FROM expense_invoices
                WHERE status IN ('pending', 'pending_receipt', 'manager_approved')
                  AND created_at < NOW() - INTERVAL '3 days'
            """)
            )
            row = r2.one()
            full_count = int(row[0] or 0)
            full_total = float(row[1] or 0)
            return {
                "count": full_count,
                "total_amount": full_total,
                "items": items,
            }
        except Exception:
            raise

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
