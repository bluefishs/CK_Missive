"""
Regression：morning_report 逾期計算基準修正（2026-04-22）

事故：115年_派工單號012 的 d.deadline 是舊發文日，但 work_record.deadline_date
為 4/29（未來）。原本演算法用 d.deadline 算得 overdue_days=47 → 誤判逾期。

修復：_get_overdue_items 優先用 next_event_date（work_record 實際交付期限），
warning 獨立桶（有律定且 ≤ 7 天，不再混入逾期）。

本測試透過靜態程式碼掃描驗證修正邏輯仍存在（避免重構後被打回原型）。
"""
from pathlib import Path


def _read_service():
    p = Path(__file__).resolve().parents[2] / "app" / "services" / "ai" / "domain" / "morning_report_service.py"
    return p.read_text(encoding="utf-8")


def test_overdue_uses_next_event_as_primary_basis():
    """effective_dl 應優先取 next_event_date，而非 d.deadline"""
    src = _read_service()
    assert "effective_dl = next_event_date or dispatch_deadline" in src, (
        "overdue_days 應以 next_event_date 為主基準"
    )


def test_warning_closure_has_separate_bucket():
    """closure == 'warning' 不得進入 overdue_dispatches"""
    src = _read_service()
    assert "warning_items = []" in src
    assert "warning_items.append(item)" in src
    assert '"warning_count"' in src
    assert '"warning_items"' in src


def test_overdue_days_uses_effective_dl():
    src = _read_service()
    assert '"overdue_days": (today - effective_dl).days' in src


def test_formatter_renders_warning_bucket():
    """formatter 應渲染預警桶，避免資料裝載後被忽略"""
    p = Path(__file__).resolve().parents[2] / "app" / "services" / "ai" / "domain" / "morning_report_formatter.py"
    src = p.read_text(encoding="utf-8")
    assert '"warning_count"' in src or 'warning_count' in src
    assert '"warning_items"' in src or 'warning_items' in src
    assert '預警派工' in src
