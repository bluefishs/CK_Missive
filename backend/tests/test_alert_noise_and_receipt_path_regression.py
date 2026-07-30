# -*- coding: utf-8 -*-
"""Regression — 2026-07-30 覆盤三項修法

1. 收據影像路徑 SSOT：所有 writer 入庫值皆相對於 uploads/，不得自帶 "uploads/" 前綴
   （否則讀取端 `/receipt-image` 再補一次 → "uploads/uploads/..." → 檔案在卻 404）。
2. 逾期分級：陳年逾期（> STALE_OVERDUE_DAYS）不得逐筆列為 actionable。
3. 告警去重 key 穩定性：不得用會逐日變動的 title 當 key。
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


class TestReceiptPathSSOT:
    """L52 家族：跨 writer 路徑前綴一致性"""

    WRITER_FILES = [
        "app/api/endpoints/erp/expenses_io.py",
        "app/services/integration/line_image_handler.py",
    ]

    def test_no_writer_stores_uploads_prefix(self):
        """入庫欄位 receipt_image_path 不得被賦予 "uploads/..." 字面值"""
        offenders = []
        for rel in self.WRITER_FILES:
            src = _read(rel)
            for m in re.finditer(
                r'receipt_image_path\s*=\s*(?:f?["\'])(uploads/[^"\']*)', src
            ):
                offenders.append(f"{rel}: {m.group(1)}")
        assert not offenders, (
            "receipt_image_path 入庫值必須相對於 uploads/（如 receipts/x.jpg）；"
            f"發現自帶前綴者：{offenders}"
        )

    def test_reader_still_resolves_relative_paths(self):
        """讀取端維持「相對路徑補 uploads/」的約定（本測試鎖住雙方契約）"""
        src = _read("app/api/endpoints/erp/expenses_io.py")
        assert 'Path("uploads")' in src, "讀取端補 uploads/ 前綴的邏輯被移除，SSOT 契約破裂"


class TestStaleOverdueGrading:
    """告警噪音迴圈：每日 66 筆 → 陳年項目彙總"""

    def test_threshold_constant_exists(self):
        src = _read("app/services/ai/proactive/proactive_triggers.py")
        assert "STALE_OVERDUE_DAYS" in src

    def test_overdue_query_bounded_by_threshold(self):
        """逾期查詢必須有下界，否則永遠只撈到最老那批（擠掉近期真的該處理的）"""
        src = _read("app/services/ai/proactive/proactive_triggers.py")
        assert "stale_cutoff" in src
        assert "DocumentCalendarEvent.end_date >= stale_cutoff" in src

    def test_closed_statuses_include_ignored(self):
        """歷史案件註記忽略後不得再產生告警"""
        src = _read("app/services/ai/proactive/proactive_triggers.py")
        assert '"ignored"' in src
        assert "status.notin_(_CLOSED_EVENT_STATUSES)" in src


class TestDedupeKeyStability:
    """去重 key 不可用逐日變動的字串"""

    def test_scheduler_dedupe_key_uses_entity_not_title(self):
        src = _read("app/core/scheduler.py")
        m = re.search(r"dedupe_key = \(\s*(.+?)\s*\)", src, re.S)
        assert m, "吹哨者未設定 dedupe_key"
        expr = m.group(1)
        # 主要分支必須以 alert_type + entity_type + entity_id 組成
        assert "alert.alert_type" in expr and "alert.entity_id" in expr, (
            "dedupe_key 必須用穩定識別；title 含「已逾期 573→574 天」每日變動，"
            "用它當 key 去重必然失效"
        )

    def test_helper_supports_dedupe(self):
        src = _read("app/services/notification/helpers.py")
        assert "dedupe_key" in src
        assert "is_read.is_(False)" in src, "去重應只針對未讀通知，已讀的不該被複寫"


class TestTenderProducerContract:
    """契約規則 2 + 4b：合理空要說得出原因、失敗要 raise"""

    def test_job_returns_reason_when_disabled(self):
        src = _read("app/core/scheduler.py")
        assert '"reason": "line_push_disabled"' in src

    def test_job_reraises_on_failure(self):
        src = _read("app/core/scheduler.py")
        idx = src.find("async def tender_business_recommend_job")
        assert idx > 0
        body = src[idx: idx + 2500]
        assert "raise" in body, "失敗必須 raise，否則 @tracked_job 記成 success（沉默成功）"
