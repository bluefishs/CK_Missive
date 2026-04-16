# -*- coding: utf-8 -*-
"""Morning Report Formatter — 晨報摘要文字格式化

從 morning_report_service.py 拆分。
純函數邏輯，不依賴 DB / async — 可單獨測試。

Responsibility:
- format_summary(): 將 sections dict 渲染為 Telegram-friendly 文字
- _compute_today_schedule(): 會議/現勘分桶 + 衝突偵測
- _parse_roc_date(): ROC 日期解析
- _format_dispatch_progress(): 派工進度標籤組合
- _format_event_time(): 會議/現勘時間格式化
- _is_site_visit(): 現勘關鍵字偵測

Version: 1.0.0 (拆分自 morning_report_service.py)
"""
import re
from datetime import date, datetime
from typing import Any, Dict, Optional, Set
from zoneinfo import ZoneInfo

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

# 現勘關鍵字 (與 service.py 同步)
_SITE_VISIT_KEYWORDS = (
    "現勘", "會勘", "勘查", "勘驗", "現場", "踏勘", "鑑界",
    "界址", "界樁", "複丈", "鑑定",
)


def _now_taipei() -> datetime:
    return datetime.now(TZ_TAIPEI)


class MorningReportFormatter:
    """晨報摘要格式化器 — 純函數，無 DB 依賴。"""

    _SITE_VISIT_KEYWORDS = _SITE_VISIT_KEYWORDS

    def format_summary(
        self,
        data: Dict[str, Any],
        sections: Optional[Set[str]] = None,
    ) -> str:
        """生成晨報摘要文字。

        Args:
            data: generate_report() 回傳的 sections dict
            sections: 限定渲染範圍（None = 預設 4 主題）

        Returns:
            Telegram-friendly 文字摘要
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

        parts: list[str] = []
        sections_detail: list[list[str]] = []

        def _team_tag(item: dict) -> str:
            su = item.get("survey_unit", "")
            return f"({su[:2]})" if su else ""

        # ── 1. 派工事件 ──
        dd = data.get("dispatch_deadlines", {}) if _on("dispatch") else {}
        sec: list[str] = []
        if dd.get("week_count", 0) > 0:
            parts.append(f"本週到期派工 {dd['week_count']} 筆")
            sec.append("【1. 派工事件】")
            for item in dd.get("week_items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = "🔴 今日" if days == 0 else f"⏰ 剩 {days} 天"
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                sec.append(
                    f"  {urgency} {item['dispatch_no']}{_team_tag(item)} — "
                    f"{item.get('sub_case') or item.get('project_name', '')}"
                    f" (承辦: {item.get('handler', '未指定')}，到期: {item['deadline']})"
                    f"{progress_tag}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 2a. 逾期派工 ──
        ov = data.get("overdue_items", {}) if _on("dispatch") else {}
        sec = []
        if ov.get("dispatch_count", 0) > 0:
            parts.append(f"逾期派工 {ov['dispatch_count']} 筆")
            for item in ov.get("dispatch_items", [])[:5]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                sec.append(
                    f"  🚨 逾期 {item['overdue_days']} 天 {item['dispatch_no']}{_team_tag(item)} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 2b. 待結案確認 ──
        sec = []
        pc = ov.get("pending_closure_count", 0) if _on("dispatch") else 0
        if pc > 0:
            parts.append(f"待結案確認 {pc} 筆")
            for item in ov.get("pending_closure_items", [])[:3]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                sec.append(
                    f"  📋 待結案 {item['dispatch_no']} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 3. 會議事件 ──
        mt = data.get("upcoming_meetings", {}) if _on("meeting") else {}
        sec = []
        if mt.get("count", 0) > 0:
            parts.append(f"近期會議 {mt['count']} 場")
            sec.append("【2. 會議事件】")
            for item in mt.get("items", [])[:5]:
                days = item.get("days_left", 0)
                urgency = (
                    "🔔 今日" if days == 0
                    else "📅 明日" if days == 1
                    else f"📅 {days} 天後"
                )
                time_str = item.get("time_str") or item.get("start_date", "")
                location = f" @ {item['location']}" if item.get("location") else ""
                sec.append(f"  {urgency} {time_str} {item['title']}{location}")
        if sec:
            sections_detail.append(sec)

        # ── 4. 近期現勘 ──
        sv = data.get("upcoming_site_visits", {}) if _on("site_visit") else {}
        sec = []
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
                sec.append(f"  {urgency} {time_str} {item['title']}{location}{source}")
        if sec:
            sections_detail.append(sec)

        # ── 5. 排程事件 ──
        sec = []
        sc = ov.get("scheduled_count", 0) if _on("dispatch") else 0
        if sc > 0:
            parts.append(f"排程作業 {sc} 筆")
            sec.append("【3. 排程事件】")
            for item in ov.get("scheduled_items", [])[:5]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                next_ev = item.get("next_event", "")
                next_tag = f" → 交付期限 {next_ev}" if next_ev else ""
                sec.append(
                    f"  📅 {item['dispatch_no']}{_team_tag(item)} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')})"
                    f"{progress_tag}{next_tag}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 6. 今日分桶 + 衝突 ──
        ts = data.get("today_schedule", {})
        sec = []
        if ts.get("total", 0) > 0:
            morning = ts.get("morning", 0)
            afternoon = ts.get("afternoon", 0)
            evening = ts.get("evening", 0)
            tod = []
            if morning:
                tod.append(f"上午 {morning}")
            if afternoon:
                tod.append(f"下午 {afternoon}")
            if evening:
                tod.append(f"晚間 {evening}")
            parts.append(f"今日行程 {ts['total']} 場（{'/'.join(tod) or '時段未定'}）")
            if ts.get("overload"):
                sec.append(f"  📛 今日 {ts['total']} 場行程超載（>=5），建議提前協調")
            for conflict in ts.get("conflicts", [])[:3]:
                sec.append(
                    f"  ⚠️ 衝突：{conflict['a_time']} {conflict['a_title']} "
                    f"與 {conflict['b_time']} {conflict['b_title']}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 7. 遺漏建檔 ──
        mc = data.get("missing_calendar_events", {}) if _on("missing") else {}
        sec = []
        if mc.get("count", 0) > 0:
            parts.append(f"⚠️ 公文未建行事曆 {mc['count']} 件")
            for item in mc.get("items", [])[:3]:
                sec.append(
                    f"  📭 {item['doc_number']} {item['subject']}"
                    f"（{item['category']}，收文 {item['days_ago']} 天）"
                )
        if sec:
            sections_detail.append(sec)

        # ── 8. PM 逾期里程碑 ──
        if _on("pm_milestone"):
            pm = data.get("pm_overdue_milestones", {}) or {}
            sec = []
            if pm.get("count", 0) > 0:
                parts.append(f"PM 逾期里程碑 {pm['count']} 項")
                for item in pm.get("items", [])[:5]:
                    sec.append(
                        f"  🏁 逾期 {item['overdue_days']} 天 {item['case_code']} "
                        f"{item['milestone_name']}（{item['status']}）"
                    )
            if sec:
                sections_detail.append(sec)

        # ── 9. ERP 待審費用 ──
        if _on("erp_expense"):
            ex = data.get("erp_pending_expenses", {}) or {}
            sec = []
            if ex.get("count", 0) > 0:
                total = ex.get("total_amount", 0)
                parts.append(f"ERP 待審費用 {ex['count']} 筆 (合計 NT$ {int(total):,})")
                for item in ex.get("items", [])[:3]:
                    sec.append(
                        f"  💰 {item['inv_num']} NT$ {int(item['amount']):,} "
                        f"〔{item['status']}〕{item['uploader']}"
                    )
            if sec:
                sections_detail.append(sec)

        if not parts:
            return f"📋 {_now_taipei().strftime('%m/%d')} 晨報：今日無待處理派工/會議/現勘事項。👍"

        header = f"📋 {_now_taipei().strftime('%m/%d')} 晨報\n"
        summary_line = " | ".join(parts)
        separator = "\n  ─────────────────"
        detail_text = separator.join(
            "\n".join(lines) for lines in sections_detail if lines
        )
        report = f"{header}\n📊 {summary_line}\n"
        if detail_text:
            report += f"\n{detail_text}\n"
        return report

    # ── Utility methods ──

    @staticmethod
    def _parse_roc_date(s: str) -> Optional[date]:
        """Parse ROC date string like '115/04/17' or '115年01月15日' to date."""
        m = re.match(r'(\d{2,3})\D+(\d{1,2})\D+(\d{1,2})', s or '')
        if m:
            try:
                return date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def _format_dispatch_progress(
        milestone_type, work_category, status, has_in, has_out
    ) -> str:
        """組合派工當前作業進度標籤。"""
        stage_map = {
            "closed": "已結案", "final_approval": "最終驗收完成",
            "submit_result": "提送成果", "review_meeting": "審查會議",
            "negotiation": "協商中", "boundary_survey": "界址測量",
            "survey": "查估", "revision": "修正中", "dispatch": "派工通知",
        }
        cat_map = {
            "admin_notice": "行政通知", "dispatch_notice": "派工通知",
            "work_result": "成果回函", "meeting_notice": "會議通知",
            "meeting_record": "會議紀錄", "survey_notice": "現勘通知",
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

        if has_out:
            doc_str = "已對應發文"
        elif has_in:
            doc_str = "僅有來文"
        else:
            doc_str = "無公文對照"

        return f"{stage_str} / {doc_str}"

    def _compute_today_schedule(self, meetings: dict, site_visits: dict) -> dict:
        """合併今日會議 + 現勘，分桶 + 衝突偵測。"""
        today_items = []
        for src_name, src in (("meeting", meetings), ("site_visit", site_visits)):
            for item in src.get("items", []):
                if item.get("days_left") != 0:
                    continue
                time_str = item.get("time_str") or ""
                hour = None
                minute = 0
                m = re.search(r"(\d{2}):(\d{2})", time_str)
                if m:
                    hour = int(m.group(1))
                    minute = int(m.group(2))
                today_items.append({
                    "kind": src_name, "title": item.get("title", ""),
                    "time_str": time_str, "hour": hour, "minute": minute,
                    "location": item.get("location", ""),
                })

        morning_count = sum(1 for x in today_items if x["hour"] is not None and x["hour"] < 12)
        afternoon_count = sum(1 for x in today_items if x["hour"] is not None and 12 <= x["hour"] < 18)
        evening_count = sum(1 for x in today_items if x["hour"] is not None and x["hour"] >= 18)

        scheduled = sorted(
            [x for x in today_items if x["hour"] is not None],
            key=lambda x: x["hour"] * 60 + x["minute"],
        )
        conflicts = []
        for i in range(len(scheduled) - 1):
            a, b = scheduled[i], scheduled[i + 1]
            gap = (b["hour"] * 60 + b["minute"]) - (a["hour"] * 60 + a["minute"])
            if gap < 30:
                conflicts.append({
                    "a_title": a["title"], "a_time": a["time_str"],
                    "b_title": b["title"], "b_time": b["time_str"],
                    "gap_minutes": gap,
                })

        total = len(today_items)
        return {
            "total": total, "morning": morning_count, "afternoon": afternoon_count,
            "evening": evening_count, "morning_count": morning_count,
            "afternoon_count": afternoon_count, "evening_count": evening_count,
            "overload": total >= 5, "conflicts": conflicts, "items": today_items,
        }

    def _format_event_time(self, start_dt, all_day: bool) -> str:
        if not start_dt:
            return ""
        if all_day:
            return start_dt.strftime("%m/%d") + " 全天"
        return start_dt.strftime("%m/%d %H:%M")

    def _is_site_visit(self, title: str) -> bool:
        return any(k in (title or "") for k in self._SITE_VISIT_KEYWORDS)
