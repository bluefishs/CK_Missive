# -*- coding: utf-8 -*-
"""
LINE 推播鏈 Regression Tests（2026-06-03 / Lesson L64）

鎖定「夜間吹哨者 → LINE 推播」整條鏈的三個 silent failure：

1. broadcast_to_admins 缺方法
   - subscription_scheduler.py:124 呼叫 line_service.broadcast_to_admins(...)
     但 LineBotService 從未定義 → AttributeError → 標案 LINE 推播自 2026-05-25
     起 silent 失敗 ~9 天（backend-error.log 每日 08:00/18:00 各一筆 warning）。

2. ProactiveTriggerService 子檢查吞錯未 rollback
   - check_recommendations / predict_risks except 區塊吞錯後未 rollback，
     污染共用 session → 後續 query 與 LINE 推播段全撞
     InFailedSQLTransactionError（silent）。此為 2026-01-09
     BUGFIX_TRANSACTION_POLLUTION 的復發（family，見 L64）。

3. scheduler 重複掃描 ERP
   - proactive_trigger_scan_job 原本 base_service.scan_all() + erp_scanner.scan_all()
     各掃一次，但 scan_all() 內部（proactive_triggers.py:66-69）已掃 ERP →
     (a) ERP alert 重複兩份 (b) 第二次用同一 session 撞 InFailedSQLTransactionError。

對應 ADR-0028（每個 silent failure 修復必附 regression lock）。
"""
import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. broadcast_to_admins 契約 — 鎖定 AttributeError regression
# ---------------------------------------------------------------------------
class TestLineBroadcastToAdmins:
    def test_method_exists(self):
        """LineBotService 必須有 broadcast_to_admins（subscription_scheduler 依賴）。"""
        from app.services.integration.line_bot import LineBotService

        assert hasattr(LineBotService, "broadcast_to_admins"), (
            "broadcast_to_admins 缺失 → 標案 LINE 推播 AttributeError silent 失敗（L64）"
        )

    def test_scheduler_caller_contract(self):
        """subscription_scheduler 仍呼叫 broadcast_to_admins — 契約存在性鎖定。"""
        src = (
            BACKEND_ROOT / "app" / "services" / "tender" / "subscription_scheduler.py"
        ).read_text(encoding="utf-8")
        assert "broadcast_to_admins" in src, (
            "呼叫端不再使用 broadcast_to_admins？請同步本測試與 line_bot.py 契約"
        )

    @pytest.mark.asyncio
    async def test_returns_zero_when_disabled(self):
        """LINE 未啟用時回 0，不拋例外。"""
        from app.services.integration.line_bot import LineBotService

        svc = LineBotService()
        # 強制 disabled，避免依賴環境變數
        svc._enabled = False
        assert await svc.broadcast_to_admins("test") == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_admin_uid(self, monkeypatch):
        """啟用但無 LINE_ADMIN_USER_ID 時回 0（warning 跳過，不拋例外）。"""
        from app.services.integration.line_bot import LineBotService

        svc = LineBotService()
        monkeypatch.setattr(type(svc), "enabled", property(lambda self: True))
        monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)
        assert await svc.broadcast_to_admins("test") == 0

    @pytest.mark.asyncio
    async def test_returns_one_on_success(self, monkeypatch):
        """啟用 + 有 admin uid + push 成功 → 回 1。"""
        from app.services.integration.line_bot import LineBotService

        svc = LineBotService()
        monkeypatch.setattr(type(svc), "enabled", property(lambda self: True))
        monkeypatch.setenv("LINE_ADMIN_USER_ID", "U_admin_test")
        svc.push_message = AsyncMock(return_value=True)

        result = await svc.broadcast_to_admins("hello admin")
        assert result == 1
        svc.push_message.assert_awaited_once_with("U_admin_test", "hello admin")


# ---------------------------------------------------------------------------
# 2. ProactiveTriggerService session 隔離 — 鎖定交易污染 regression
# ---------------------------------------------------------------------------
class TestProactiveSessionIsolation:
    @pytest.mark.asyncio
    async def test_check_recommendations_rolls_back_on_error(self):
        """子檢查拋錯時必須 rollback 共用 session（否則污染後續 query）。"""
        from app.services.ai.proactive.proactive_triggers import ProactiveTriggerService

        db = AsyncMock()
        svc = ProactiveTriggerService(db)

        with patch(
            "app.services.ai.proactive.proactive_recommender.ProactiveRecommender"
        ) as MockRec:
            MockRec.return_value.scan_recommendations = AsyncMock(
                side_effect=RuntimeError("boom")
            )
            alerts = await svc.check_recommendations()

        assert alerts == []  # 吞錯後回空，不拋例外
        db.rollback.assert_awaited_once()  # 關鍵：必須 rollback

    @pytest.mark.asyncio
    async def test_predict_risks_rolls_back_on_error(self):
        """predict_risks 拋錯時同樣必須 rollback。"""
        from app.services.ai.proactive.proactive_triggers import ProactiveTriggerService

        db = AsyncMock()
        # 讓內部第一個 db.execute 即拋錯，觸發 except 區塊
        db.execute = AsyncMock(side_effect=RuntimeError("boom"))
        svc = ProactiveTriggerService(db)

        alerts = await svc.predict_risks()

        assert alerts == []
        db.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# 3. scheduler 不得重複掃描 ERP — 鎖定 double-scan regression
# ---------------------------------------------------------------------------
class TestSchedulerNoDoubleErpScan:
    def test_proactive_job_does_not_reconstruct_erp_scanner(self):
        """proactive_trigger_scan_job 不得再獨立 new ERPTriggerScanner
        （scan_all 內部已掃 ERP；重複會雙份 alert + 同 session 撞交易錯）。"""
        src = (BACKEND_ROOT / "app" / "core" / "scheduler.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        target = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "proactive_trigger_scan_job":
                target = node
                break
        assert target is not None, "找不到 proactive_trigger_scan_job"

        job_src = ast.get_source_segment(src, target) or ""
        assert "ERPTriggerScanner(" not in job_src, (
            "scheduler 重複建構 ERPTriggerScanner → ERP alert 雙份 + 共用 session "
            "撞 InFailedSQLTransactionError（L64）。scan_all() 內部已掃 ERP。"
        )
