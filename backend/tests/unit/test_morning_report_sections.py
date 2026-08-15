"""晨報段落編號必須依實際渲染順序，且每個明細區塊都要有標題。

2026-08-15：三個標題寫死【1.】【2.】【3.】，而每段都是條件渲染 ——
今天沒有派工到期、沒有會議，訊息裡就只出現孤零零的「3. 排程事件」，
讀起來像前兩段壞掉。編號是**位置**的函數，不該寫死。
另外預警派工與待審費用兩段原本完全沒有標題。
"""
import re

from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

_NUM = re.compile(r"【(\d+)\. ")


def _render(data):
    return MorningReportFormatter().format_summary(data, sections={"all"})


def _headers(text):
    return [int(n) for n in _NUM.findall(text)]


def test_numbering_is_contiguous_when_early_sections_empty():
    """只有排程事件有資料時，它必須是【1.】而不是【3.】。"""
    text = _render({
        "dispatch_deadlines": {"week_count": 0, "week_items": []},
        "overdue_items": {
            "scheduled_count": 1,
            "scheduled_items": [{"dispatch_no": "X1", "project_name": "P",
                                 "handler": "H", "survey_unit": "乾坤"}],
        },
    })
    assert _headers(text) == [1], f"編號不連續: {_headers(text)}｜{text}"


def test_every_detail_block_has_a_header():
    """三段都有資料時，編號必須是 1,2,3 且沒有無標題區塊。"""
    text = _render({
        "dispatch_deadlines": {
            "week_count": 1,
            "week_items": [{"dispatch_no": "A", "project_name": "P",
                            "handler": "H", "survey_unit": "乾坤", "days_left": 2,
                            "deadline": "2026-08-20"}],
        },
        "overdue_items": {
            "scheduled_count": 1,
            "scheduled_items": [{"dispatch_no": "B", "project_name": "Q",
                                 "handler": "H", "survey_unit": "威名"}],
        },
        "erp_pending_expenses": {
            "count": 1, "total_amount": 3200,
            "items": [{"amount": 3200, "category": "差旅費",
                       "status": "pending", "inv_num": "DN03384512"}],
        },
    })
    nums = _headers(text)
    assert nums == list(range(1, len(nums) + 1)), f"編號跳號: {nums}"
    # 每個分隔區塊都該帶標題
    blocks = [b for b in text.split("─────────────────") if b.strip()]
    # 分隔線把訊息切成 N 段，每一段都該帶一個標題（首段含表頭與摘要行）
    assert len(nums) == len(blocks), f"有區塊沒有標題: 標題 {len(nums)} 段 {len(blocks)}"


def test_invoice_number_is_not_masked_away():
    """發票號給末 4 碼 —— 完整號碼會被遮蔽器當成身分證整串換掉。"""
    from app.services.common.telegram_content_sanitizer import sanitize
    text = _render({
        "erp_pending_expenses": {
            "count": 1, "total_amount": 3200,
            "items": [{"amount": 3200, "category": "差旅費",
                       "status": "pending", "inv_num": "DN03384512"}],
        },
    })
    out = sanitize(text)
    assert "DN03384512" not in out
    assert "末4碼 4512" in out, f"發票末碼不見了: {out}"
    assert "[識別碼]" not in out, "發票號又被整串遮掉了"
