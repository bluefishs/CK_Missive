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


# 費用狀態的中文對照。晨報是給人看的 LINE 訊息，`manager_approved` 這種
# 內部代碼直接印出來，讀的人得自己翻譯。
# ⚠️ 這張表必須涵蓋 expense_invoices.status 的**每一個**實際值。
# 漏掉的會走 fallback 印出英文原值 —— 中文訊息裡冒出 `〔finance_approved〕`，
# 不會拋錯、不會有人發現，只是讀起來突然變成英文。
# 2026-08-15 補 `verified` 與 `finance_approved`（審批四層裡的第二、第四層），
# 它們自審批流上線起就一直漏著，而當下 DB 裡正好有 3 筆是這兩個狀態。
# 新增審批狀態時，這張表要一起改 —— 由 test_expense_status_zh_covers_all 守著。
# 段落標題佔位符：真正的編號在組裝時依實際渲染順序填入（見 format_summary 結尾）
_SECTION_MARK = "【#. "

# 2026-08-17 owner「流程簡化」後更正：
#   · `verified` 是**終態**，不是「待主管」—— 原本寫「已初核・待主管」是錯的，
#     那筆其實已經結束並入帳了，而訊息叫人去等一個不存在的下一步。
#   · `manager_approved` 不再「待財務」（財務層已移除），現在是待最後確認。
_EXPENSE_STATUS_ZH = {
    "pending": "待審",
    "pending_receipt": "待補收據",
    "verified": "已完成・已入帳",
    "manager_approved": "主管已核准・待確認",
    "finance_approved": "待確認（舊流程）",
    "approved": "已核准",
    "rejected": "已駁回",
}


def _amount_band(amount: int) -> str:
    """把金額換成決策級距 —— **輸出不含任何數字**。

    分界取自系統既有的審批門檻，不另訂一組（那會是第二份事實）：

        ≤ AUTO_APPROVE_BELOW   免審直達      → 「小額」
        < APPROVAL_THRESHOLD   一般審批      → 「一般」
        ≥ APPROVAL_THRESHOLD   需主管核准    → 「需主管核准」⚠️

    ⚠️ 這些標籤會通過 `telegram_content_sanitizer`，必須確保**沒有數字**，
    否則會被遮成 `[金額]` 而前功盡棄。有測試守著（`test_amount_band_no_digits`）。
    """
    from app.schemas.erp.expense import APPROVAL_THRESHOLD, AUTO_APPROVE_BELOW

    if amount <= 0:
        return "金額未填"
    if amount <= int(AUTO_APPROVE_BELOW):
        return "小額"
    if amount < int(APPROVAL_THRESHOLD):
        return "一般"
    return "需主管核准⚠️"


def _format_expense_line(item: dict) -> str:
    """待審費用一行。

    2026-08-05 owner：「無法得知是既事由」—— 原本只印發票號、金額、狀態代碼、
    上傳者，**看不出這筆是什麼支出**。而 `category`（差旅費…）與 `notes`
    （如「派工單018地上物調查」）**查詢早就撈出來了，只是沒有顯示** ——
    又一次「資料在，缺的是出口」。

    欄位順序依「早上瞄一眼要先知道什麼」排：事由 → 金額 → 狀態 → 誰 → 憑證號。
    發票號放最後但**保留**，因為那是回系統查這筆的鍵。
    """
    amount = int(item.get("amount") or 0)
    category = (item.get("category") or "").strip() or "未分類"
    # 狀態為空時原本會留下 `〔〕` 空括號 —— owner 2026-08-17 貼出的訊息
    # 正是這個形狀（`差旅費 [金額]〔〕｜`）。沒有值就不要留框。
    status = _EXPENSE_STATUS_ZH.get(item.get("status"), (item.get("status") or "").strip())
    who = (item.get("uploader") or "").strip()

    # 金額改為**級距**（2026-08-17）。
    #
    # 推播一律經 `telegram_content_sanitizer` 遮蔽 —— 那是必要的，
    # owner 的 Telegram 帳號就是因為金額呈現被判定為非正常金流而永久封禁。
    # 但遮完之後訊息裡只剩 `[金額]`，**300 元和 50 萬長得一模一樣**，
    # 早上瞄一眼完全無法判斷哪筆該先處理 —— 遮蔽解決了風險，卻讓訊息失去用途。
    #
    # 級距用的是**系統自己的審批門檻**（`AUTO_APPROVE_BELOW` / `APPROVAL_THRESHOLD`），
    # 不是我另訂一組數字：讀的人真正要知道的是「這筆要不要我簽」。
    # 級距標籤裡**沒有任何數字**，不構成金流樣式。
    band = _amount_band(amount)
    seg = [f"  💰 {category} {band}"]
    if status:
        seg.append(f"〔{status}〕")
    else:
        # 沒有狀態時要補一個分隔，否則「小額」與人名會黏成「小額未指定上傳者」
        seg.append(" ")
    seg.append(who or "未指定上傳者")
    parts = ["".join(seg)]
    reason = (item.get("reason") or "").strip()
    if reason:
        parts.append(f"｜{reason}")
    # 發票號只給末 4 碼。完整號碼（如 DN03384512＝2 字母 + 8 數字）會撞上
    # 遮蔽器的身分證樣式，被整串換成 [識別碼] —— 那個欄位的用途就沒了，
    # 而它本來是「回系統查這筆」的鍵（見本函式 docstring）。
    # 末 4 碼配上事由與日期已足以定位，且不再構成完整 ID 樣式。
    _inv = (item.get("inv_num") or "").strip()
    if _inv:
        parts.append("｜末4碼 " + _inv[-4:])
    return "".join(parts)


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

        # ── 0. 財務對帳告警（2026-08-29）──
        # 刻意**不受 sections 篩選**：這種告警曾連發 5 天無人接
        # （AR 虛增 1,681 萬期間），它需要的是必達，不是可訂閱。
        ra = data.get("reconciliation_alerts", {})
        sec0: list[str] = []
        if ra.get("count", 0) > 0:
            parts.append(f"⚠️ 財務對帳告警 {ra['count']} 則")
            sec0.append(_SECTION_MARK + "財務對帳告警】")
            for item in ra.get("items", [])[:3]:
                sec0.append(f"  🔴 {item.get('title', '')} — {item.get('message', '')[:80]}")
        if sec0:
            sections_detail.append(sec0)

        # ── 1. 派工事件 ──
        dd = data.get("dispatch_deadlines", {}) if _on("dispatch") else {}
        sec: list[str] = []
        if dd.get("week_count", 0) > 0:
            parts.append(f"本週到期派工 {dd['week_count']} 筆")
            sec.append(_SECTION_MARK + "派工事件】")
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

        # ── 2b. 預警派工（v5.8.1 新增）：有律定期限且 ≤ 7 天 ──
        sec = []
        wc = ov.get("warning_count", 0) if _on("dispatch") else 0
        if wc > 0:
            parts.append(f"預警派工 {wc} 筆")
            # 2026-08-15：這段原本也沒有標題，於是它佔了第 1 個位置
            # 而編號從【2.】開始 —— 每個明細區塊都要有標題，否則
            # 「位置」與「編號」就會對不起來，看起來像少了一段。
            sec.append(_SECTION_MARK + "預警派工】")
            for item in ov.get("warning_items", [])[:5]:
                progress = item.get("progress", "")
                progress_tag = f" 〔{progress}〕" if progress else ""
                next_ev = item.get("next_event", "")
                next_tag = f"，期限 {next_ev}" if next_ev else ""
                sec.append(
                    f"  🟠 預警 {item['dispatch_no']}{_team_tag(item)} — "
                    f"{item.get('project_name', '')} (承辦: {item.get('handler', '未指定')}{next_tag})"
                    f"{progress_tag}"
                )
        if sec:
            sections_detail.append(sec)

        # ── 2c. 待結案確認 ──
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
            sec.append(_SECTION_MARK + "會議事件】")
            for item in mt.get("items", [])[:5]:
                days = item.get("days_left", 0)
                # v5.8.1：會議用 🤝（協作），與排程事件 📅 區隔
                urgency = (
                    "🔔 今日" if days == 0
                    else "🤝 明日" if days == 1
                    else f"🤝 {days} 天後"
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
            sec.append(_SECTION_MARK + "排程事件】")
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
                # 2026-08-15：這段原本**完全沒有標題** —— 其他段都有【N. …】，
                # 只有費用是一排 💰 直接接在分隔線後面，讀的人不知道那是什麼。
                sec.append(_SECTION_MARK + "待審費用】")
                for item in ex.get("items", [])[:3]:
                    sec.append(_format_expense_line(item))
            if sec:
                sections_detail.append(sec)

        if not parts:
            return f"📋 {_now_taipei().strftime('%m/%d')} 晨報：今日無待處理派工/會議/現勘事項。👍"

        header = f"📋 {_now_taipei().strftime('%m/%d')} 晨報\n"
        summary_line = " | ".join(parts)
        # 2026-04-22：分隔線前後加空行，避免段落緊貼
        separator = "\n\n─────────────────\n"
        # 2026-08-15：段落編號改為**依實際渲染順序推導**。
        # 原本三個標題寫死【1.】【2.】【3.】，而每一段都是條件渲染 ——
        # 今天沒有派工到期、沒有會議，訊息裡就只出現孤零零的「3. 排程事件」，
        # 讀起來像是前兩段壞掉或漏掉了。編號是**位置**的函數，不該寫死。
        _rendered = [lines for lines in sections_detail if lines]
        _numbered = []
        for _i, _lines in enumerate(_rendered, 1):
            _numbered.append(chr(10).join(
                ln.replace(_SECTION_MARK, f"【{_i}. ", 1) if _SECTION_MARK in ln else ln
                for ln in _lines
            ))
        detail_text = separator.join(_numbered)
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
